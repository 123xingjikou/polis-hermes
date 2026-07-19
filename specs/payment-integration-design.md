# Polis-Hermes 支付接入系统设计

**版本:** 1.0.0
**日期:** 2026-07-19
**状态:** APPROVED

## 1. 概述

本文档描述 Polis-Hermes 系统的支付接入系统设计。在现有 monetization 决策引擎基础上，新增面向 Stripe（国际）和 Alipay（国内）的支付能力，实现应用内购买、自动许可证签发、订阅管理。

### 1.1 背景

现有系统已完成：
- 智能体收费决策引擎（8 因子加权）
- 4 定价等级（Community / Professional / Enterprise / Sovereign）
- 许可证管理系统（AES-256-GCM 加密 + 设备绑定）

尚缺：
- 实际支付渠道接入
- 用户订阅生命周期管理
- 订单与交易记录

### 1.2 目标与范围

**目标：**
- 国内外用户可通过 Stripe / Alipay 完成支付
- 支付失败后自动签发 AES-256-GCM 许可证并邮件发送
- 交易记录落 SQLite，支持对账
- 架构可扩展（后续加微信支付 / PayPal 不改动现有代码）

**范围：**
- 新增 `payment/` 子包（ monetization 下的 payment 模块）
- 新增 3 张 SQLite 表（users、orders、subscriptions）
- 新增 5 个 REST API 端点
- 新增 Webhook 回调处理
- 新增邮件自动发送

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    应用层 (前端/CLI)                       │
│  购买按钮 → /create-checkout → 跳转支付页                   │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                  Payment Orchestrator                    │
│   路由支付请求 + 管理订阅生命周期 + 发放许可证               │
└───────────────────────┬─────────────────────────────────┘
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
┌────────────────────┐  ┌────────────────────┐
│   Stripe Adapter   │  │   Alipay Adapter   │
│  (国际信用卡支付)    │  │  (国内支付宝支付)    │
└────────────────────┘  └────────────────────┘
              │                    │
              └─────────┬──────────┘
                        ▼
              ┌────────────────────┐
              │    SQLite 数据库    │
              │  payments / orders  │
              │  / subscriptions    │
              └────────────────────┘
```

## 3. 文件结构

```
monetization/
├── __init__.py          # 扩展：导出 PaymentOrchestrator
├── config.py            # 扩展：新增 Stripe/Alipay 配置字段
├── payment/
│   ├── __init__.py
│   ├── models.py        # 数据模型（User/Order/Subscription）
│   ├── provider.py      # PaymentProvider 抽象基类 + 工厂
│   ├── stripe_adapter.py  # Stripe 实现
│   ├── alipay_adapter.py  # 支付宝实现
│   ├── orchestrator.py  # 核心编排器
│   ├── webhooks.py      # 回调处理入口
│   └── mailer.py        # 邮件发送
```

## 4. 数据模型

### 4.1 用户表 (users)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | UUID |
| github_id | TEXT UNIQUE | GitHub OAuth ID |
| email | TEXT UNIQUE | 用户邮箱 |
| name | TEXT | 显示名 |
| created_at | DATETIME | 创建时间 |

### 4.2 订单表 (orders)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | UUID |
| user_id | TEXT FK | 关联用户 |
| provider | TEXT | stripe / alipay |
| channel | TEXT | 同上，兼容字段 |
| tier | TEXT | community / professional / enterprise / sovereign |
| amount | REAL | 金额 |
| currency | TEXT | usd / cny |
| provider_order_id | TEXT UNIQUE | 渠道平台订单号 |
| status | TEXT | pending / paid / refunded / expired |
| created_at | DATETIME | |
| paid_at | DATETIME | |
| refunded_at | DATETIME | |

**索引:**
- `idx_orders_user` ON (user_id)
- `idx_orders_status` ON (status)
- UNIQUE INDEX `idx_orders_provider_order` ON (provider_order_id)

### 4.3 订阅表 (subscriptions)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | UUID |
| user_id | TEXT FK | 关联用户 |
| tier | TEXT | 当前等级 |
| status | TEXT | active / cancelled / expired / paused |
| started_at | DATETIME | |
| expires_at | DATETIME | |
| provider_subscription_id | TEXT | 渠道订阅 ID（如有） |

## 5. 组件设计

### 5.1 PaymentProvider (ABC)

```python
class PaymentProvider(ABC):
    @abstractmethod
    def create_order(self, user, tier, amount, currency) -> OrderResult: ...
    
    @abstractmethod
    def verify_callback(self, payload, headers) -> CallbackResult: ...
    
    @abstractmethod
    def refund(self, order_id, reason="") -> bool: ...
```

### 5.2 StripeAdapter

- 使用 Stripe Python SDK
- `create_order`: 创建 Stripe Checkout Session
- `verify_callback`: 验证 Stripe-Signature 头
- `refund`: 通过 Stripe API 退款

### 5.3 AlipayAdapter

- 使用 Alipay SDK（或自实现 RSA 签名）
- `create_order`: 创建支付宝当面付/电脑网站支付订单
- `verify_callback`: 用支付宝公钥验签
- `refund`: 调用 alipay.trade.refund

### 5.4 PaymentFactory

```python
def get_provider(channel: str) -> PaymentProvider:
    if channel == "stripe":
        return StripeAdapter()
    if channel == "alipay":
        return AlipayAdapter()
    raise ValueError(f"Unknown payment channel: {channel}")
```

### 5.5 Orchestrator

**核心方法:**

- `create_checkout(user_id, tier, channel)` → 返回 `OrderResult` (含 `checkout_url`)
- `handle_webhook(channel, payload, headers)` → 验证 + 更新订单 + 续期订阅 + 触发许可证签发
- `get_subscription(user_id)` → 当前订阅状态
- `list_orders(user_id, limit=50)` → 历史订单

### 5.6 Mailer

- `send_license_email(user_email, license_key, tier, expires_at)` → 发送许可证邮件
- 支持 SMTP（可扩展）
- 失败记录到 `pending_emails` 表

## 6. API 接口

### 6.1 POST /api/v1/payments/checkout

**请求:**
```json
{
  "tier": "professional",
  "channel": "stripe"
}
```

**响应:**
```json
{
  "order_id": "ord_abc123",
  "amount": 29,
  "currency": "usd",
  "checkout_url": "https://checkout.stripe.com/pay/cs_test_xxx",
  "expires_at": "2026-07-19T03:00:00Z"
}
```

### 6.2 GET /api/v1/payments/subscription

**响应:**
```json
{
  "tier": "professional",
  "status": "active",
  "started_at": "2026-07-19T02:00:00Z",
  "expires_at": "2026-08-19T02:00:00Z",
  "auto_renew": true
}
```

### 6.3 GET /api/v1/payments/history

**响应:**
```json
{
  "orders": [
    {
      "id": "ord_abc123",
      "tier": "professional",
      "amount": 29,
      "currency": "usd",
      "provider": "stripe",
      "status": "paid",
      "created_at": "2026-07-19T02:00:00Z",
      "paid_at": "2026-07-19T02:01:23Z"
    }
  ]
}
```

### 6.4 POST /api/v1/payments/stripe/webhook

- Stripe 回调端点
- 验证 Stripe-Signature
- 调用 `Orchestrator.handle_webhook("stripe", payload, headers)`

### 6.5 POST /api/v1/payments/alipay/notify

- 支付宝异步通知
- 用支付宝公钥验签
- 调用 `Orchestrator.handle_webhook("alipay", payload, headers)`

## 7. Webhook 处理流程

```
支付成功
   │
   ▼
Webhook 到达 → 路由到对应端点
   │
   ▼
verify_callback() 验证签名 + 幂等检查
   │  (失败返回 400，成功继续)
   ▼
更新订单状态: pending → paid
   ├─ 幂等：provider_order_id 唯一约束
   └─ 已 paid 则直接返回 200，不重复处理
   │
   ▼
创建 / 续期订阅记录
   │
   ▼
调用 _issue_license(user, tier)
   ├─ LicenseManager.issue() 生成 AES-256-GCM 许可证
   ├─ 绑定 user email + 当前设备指纹
   └─ 生成 license_key (格式: XXXXX-XXXXX-XXXXX-XXXXX)
   │
   ▼
Mailer.send_license_email(user_email, license_key, tier, expires_at)
   │
   ▼
返回 200 OK
```

**时序约束：**
- 端到端 < 5 秒（不含邮件网络延迟）
- 邮件发送异步（后台线程），不阻塞 HTTP 响应

## 8. 错误处理与重试

### 8.1 策略矩阵

| 场景 | 处理策略 | 重试 |
|------|---------|------|
| Webhook 签名失败 | 立即 400 返回 | 不重试 |
| 数据库写入失败 | 记录日志 + 抛异常 | 1s/5s/30s 退避，3 次 |
| 邮件发送失败 | 记录到 `pending_emails` | 后台每小时重试 |
| 许可证签发失败 | 记录到 `pending_licenses` | 后台每小时重试 |
| 网络超时（渠道 API） | SDK 内 idempotent 重试 | SDK 默认策略 |
| 订单金额不一致 | 拒绝处理 + 告警 | 不重试 |

### 8.2 后台补发任务

- 定时扫描 `pending_emails` / `pending_licenses`
- 每小时执行一次
- 重试 3 次后标记为 failed，需人工介入
- 同步 Stripe / 支付宝订单状态（对账）

### 8.3 运维监控

关键指标：
- `payment_webhook_total`（按 channel + status 标签）
- `payment_webhook_errors_total`
- `license_issue_failures_total`
- `pending_emails_queue_size`
- `pending_licenses_queue_size`

## 9. 安全设计

| 威胁 | 防护措施 |
|------|---------|
| 伪造 Webhook | Stripe 签名（Stripe-Signature）+ 支付宝公钥验签 |
| 重放攻击 | `provider_order_id` 唯一约束 + 幂等处理 |
| 金额篡改 | 服务端价格从 `config.tiers` 取，禁用前端金额入参 |
| API 越权 | Bearer token 校验，只能查询/操作自己的订单和订阅 |
| 许可证盗用 | AES-GCM 加密 + 设备指纹绑定 |
| 密钥泄露 | Webhook secret、商户私钥走 `os.getenv()`，不落盘入库 |
| 中间人攻击 | 全链路 HTTPS（Stripe / Alipay 强制） |
| 优惠券/折扣（预留） | 未来新增 coupon 表，Orchestrator 在 `create_order` 前计算最终金额 |

## 10. 适配器扩展指南

新增（例如）微信支付：

1. 新建 `wechat_adapter.py`
2. 实现 `PaymentProvider` 三个抽象方法
3. 在 `payment_factory()` 注册
4. 在 `MonetizationConfig` 新增 `wechat_*` 配置字段
5. 新增 webhook 端点：`POST /api/v1/payments/wechat/notify`

无需修改 Orchestrator 或现有 Adapter 代码。

## 11. 配置 (新增)

在 `MonetizationConfig` 中新增：

```python
# Stripe
stripe_secret_key: str = ""          # env: STRIPE_SECRET_KEY
stripe_publishable_key: str = ""     # env: STRIPE_PUBLISHABLE_KEY
stripe_webhook_secret: str = ""      # env: STRIPE_WEBHOOK_SECRET

# Alipay
alipay_app_id: str = ""              # env: ALIPAY_APP_ID
alipay_private_key: str = ""         # env: ALIPAY_PRIVATE_KEY
alipay_public_key: str = ""          # env: ALIPAY_PUBLIC_KEY
alipay_gateway: str = "https://openapi.alipay.com/gateway.do"

# SMTP (邮件)
smtp_host: str = ""                  # env: SMTP_HOST
smtp_port: int = 587                 # env: SMTP_PORT
smtp_user: str = ""                  # env: SMTP_USER
smtp_password: str = ""             # env: SMTP_PASSWORD
smtp_from: str = ""                  # env: SMTP_FROM

# Payment enabled
payment_enabled: bool = False        # env: PAYMENT_ENABLED
```

## 12. 数据库迁移

```sql
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    github_id TEXT UNIQUE,
    email TEXT UNIQUE,
    name TEXT NOT NULL DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    channel TEXT NOT NULL,
    tier TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    provider_order_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    paid_at DATETIME,
    refunded_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);

CREATE TABLE IF NOT EXISTS subscriptions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    tier TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    provider_subscription_id TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_subs_user ON subscriptions(user_id);

CREATE TABLE IF NOT EXISTS pending_emails (
    id TEXT PRIMARY KEY,
    user_email TEXT NOT NULL,
    license_key TEXT NOT NULL,
    tier TEXT NOT NULL,
    attempts INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pending_licenses (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    tier TEXT NOT NULL,
    attempts INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## 13. 依赖 (新增)

```
stripe>=7.0.0          # Stripe 支付
alipay-sdk-python>=3.0 # 支付宝（或自实现 RSA 签名）
aiosmtplib>=3.0        # 异步邮件发送（可选）
```

## 14. 测试策略

- `tests/test_payment_models.py` — 数据库模型和 CRUD
- `tests/test_provider.py` — 抽象接口一致性（StubProvider）
- `tests/test_stripe_adapter.py` — Mock Stripe SDK
- `tests/test_alipay_adapter.py` — Mock Alipay SDK
- `tests/test_orchestrator.py` — 核心流程
- `tests/test_webhooks.py` — 回调验签 + 幂等
- `tests/test_mailer.py` — 邮件发送 + 失败重试
- `tests/test_integration.py` — 端到端（使用测试渠道凭证）

## 15. 里程碑

| 阶段 | 内容 | 预估工作量 |
|------|------|-----------|
| Phase 1 | 数据模型 + 基础表结构 | 小 |
| Phase 2 | Stripe Adapter + Orchestrator | 中 |
| Phase 3 | Alipay Adapter | 中 |
| Phase 4 | Webhook + 许可证自动签发 | 中 |
| Phase 5 | 邮件发送 + 后台任务 | 小 |
| Phase 6 | 测试覆盖 + CI 集成 | 中 |

## 16. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 渠道 API 重大变更 | 适配器模式隔离，只改对应 Adapter |
| 支付回调签名实现错误 | 使用官方 SDK 验签方法，不自实现 |
| 邮件服务不稳定 | pending_emails 表 + 后台重试 |
| SQLite 写入并发 | WAL 模式 + 事务 |
| 许可证签发失败阻塞支付流程 | 许可证签发异步化，失败不阻塞订单处理 |

---

*End of Design Document*
