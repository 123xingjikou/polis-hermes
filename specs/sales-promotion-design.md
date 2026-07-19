# Polis-Hermes 智能体推销系统设计

**版本:** 1.0.0
**日期:** 2026-07-19
**状态:** APPROVED

## 1. 概述

本文档描述 Polis-Hermes 系统的智能体推销系统设计。通过扩展现有 `CityResident` Agent 基础设施，构建一个能在 Twitter、Reddit、Hacker News 上自动发布技术教程和产品故事的推销智能体。

### 1.1 背景

现有系统已完成：
- 自治认知城市架构（Agent + 记忆 + 决策）
- 智能体收费决策引擎（8 因子加权）
- 软件保护系统（许可证、代码签名、反篡改）
- 支付接入系统（Stripe + Alipay）

尚缺：
- 主动推销能力（让智能体"走出去"推广项目）
- 社交媒体存在感建设
- 潜在用户触达渠道

### 1.2 目标与范围

**目标：**
- 智能体自动生成技术教程和产品故事内容
- 通过 Browser Use 自动发布到 Twitter / Reddit / HN
- 对正面评论自动回复感谢
- 全自动化：无人值守，GitHub Actions 定时驱动

**范围：**
- 新增 `sales/` 子包（monetization 下的 sales 模块）
- 扩展 `CityResident` 为 `SalesAgent`（promoter 角色）
- 新增内容生成器、社交媒体发布器、分析追踪器
- 新增 GitHub Actions 定时发布工作流
- 凭据管理通过环境变量 + GitHub Secrets

### 1.3 用户确认的设计决策

根据需求调研确认：

| 决策项 | 选择 |
|--------|------|
| 内容策略 | 技术教程(50%) + 产品故事(30%) + 社区互动(20%) |
| Twitter 频率 | 1-2 篇/天 |
| Reddit 频率 | 2-3 篇/周 |
| HN 频率 | 1 篇/周 |
| 互动策略 | 简单点赞/感谢回复（不处理技术支持） |
| 凭据管理 | 环境变量 + GitHub Secrets（最简方案） |
| 发布方式 | Browser Use（无需 API Keys） |

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Sales Promotion Agent                        │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │  Content        │  │  Social          │  │  Analytics    │  │
│  │  Generator      │  │  Publisher       │  │  Tracker      │  │
│  │  ─────────────  │  │  ──────────────  │  │  ───────────  │  │
│  │  LLM 驱动       │  │  Playwright      │  │  SQLite 存储  │  │
│  │  多平台适配     │  │  浏览器自动化    │  │  效果追踪     │  │
│  │  内容日历       │  │  凭据注入        │  │  数据报表     │  │
│  └────────┬────────┘  └────────┬─────────┘  └───────┬───────┘  │
│           │                    │                     │           │
│           └────────────────────┴─────────────────────┘           │
│                                │                                 │
│                    ┌───────────┴───────────┐                    │
│                    │   Promotion Scheduler │                    │
│                    │   (GitHub Actions)    │                    │
│                    └───────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
         ┌──────────┐    ┌──────────┐    ┌──────────┐
         │ Twitter  │    │ Reddit   │    │ HN       │
         │ 1-2/天   │    │ 2-3/周   │    │ 1/周     │
         └──────────┘    └──────────┘    └──────────┘
```

### 2.1 组件职责

| 组件 | 职责 | 技术实现 |
|------|------|----------|
| SalesAgent | 整合所有能力，执行推销任务 | 扩展 CityResident |
| ContentGenerator | 生成平台适配的内容 | LLM + 模板系统 |
| SocialPublisher | 浏览器自动化发布 | Playwright |
| AnalyticsTracker | 追踪发布效果 | SQLite + 统计 |
| PromotionScheduler | 定时触发发布任务 | GitHub Actions |

### 2.2 文件结构

```
monetization/
├── sales/
│   ├── __init__.py           # 模块导出
│   ├── agent.py              # SalesAgent 定义
│   ├── content_generator.py  # 内容生成器
│   ├── publisher.py          # 社交媒体发布器
│   ├── platforms.py          # 平台适配器（Twitter/Reddit/HN）
│   ├── analytics.py          # 分析追踪
│   ├── credentials.py        # 凭据管理
│   └── templates.py          # 内容模板
```

## 3. SalesAgent 设计

### 3.1 Agent 定义

```python
class SalesAgent(CityResident):
    """推销智能体 - 扩展 CityResident"""

    def __init__(self, name: str, personality: dict, skills: dict):
        super().__init__(
            name=name,
            personality=personality,
            skills=skills,
            role="promoter"
        )
        # 注册推销相关能力
        self.capabilities["generate_content"] = self._generate_content
        self.capabilities["publish_post"] = self._publish_post
        self.capabilities["interact"] = self._interact_with_audience
        self.capabilities["analyze"] = self._analyze_performance
```

### 3.2 人格与角色配置

```python
PROMOTER_PERSONALITY = {
    "openness": 0.85,        # 高开放性：愿意尝试新平台/话题
    "confidence": 0.70,      # 中高自信：表达清晰有说服力
    "aggressiveness": 0.30,  # 低攻击性：友好专业形象
    "sociability": 0.80,     # 高社交性：积极互动
}

PROMOTER_SKILLS = {
    "content_creation": 0.9,   # 内容创作
    "technical_writing": 0.85, # 技术写作
    "community_engagement": 0.8, # 社区互动
    "brand_awareness": 0.75,    # 品牌意识
}
```

### 3.3 能力方法

| 能力 | 输入 | 输出 | 实现 |
|------|------|------|------|
| `generate_content` | `context` (平台, 主题, 格式) | `PostContent` | LLM + 模板 |
| `publish_post` | `PostContent`, `platform` | `PublishResult` | Playwright |
| `interact` | `platform`, `post_id` | `InteractResult` | 点赞 + 感谢回复 |
| `analyze` | `date_range` | `AnalyticsReport` | SQLite 查询 |

## 4. 内容生成器设计

### 4.1 内容类型配比

| 类型 | 比例 | 示例主题 |
|------|------|----------|
| 技术教程 | 50% | "如何用 MCP 构建自治 Agent", "RSA 代码签名实战" |
| 产品故事 | 30% | "Polis-Hermes 从 0 到 1", "为什么我们需要 Agent 收费引擎" |
| 社区互动 | 20% | "你最想要的 Agent 功能？", "投票：下一个功能做什么" |

### 4.2 平台适配策略

| 平台 | 内容风格 | 格式要求 |
|------|----------|----------|
| Twitter | 简洁有力，话题标签 | ≤280 字符，3-5 个 hashtag |
| Reddit | 深度讨论，Subreddit 适配 | r/Python, r/MachineLearning, r/selfhosted |
| HN | Show HN 格式，技术深度 | 产品演示 + 技术架构说明 |

### 4.3 内容生成流程

```
┌────────────┐    ┌────────────┐    ┌────────────┐
│ 选择内容   │───▶│ LLM 生成   │───▶│ 平台适配   │
│ 类型+主题  │    │ 原始内容   │    │ + 格式化   │
└────────────┘    └────────────┘    └────────────┘
                                              │
                        ┌──────────────────────┘
                        ▼
               ┌────────────────┐
               │ PostContent    │
               │ ────────────── │
               │ platform       │
               │ content_type   │
               │ title          │
               │ body           │
               │ hashtags       │
               │ media_urls     │
               └────────────────┘
```

## 5. 社交媒体发布器设计

### 5.1 Browser Use 策略

使用 Playwright 实现无 API Keys 的浏览器自动化：

| 平台 | 登录方式 | 发布流程 |
|------|----------|----------|
| Twitter | Cookie/账号密码 | 导航 → 点击推文框 → 输入内容 → 发送 |
| Reddit | Cookie/账号密码 | 导航 → 选择 Subreddit → 填写表单 → 提交 |
| HN | Cookie/账号密码 | 导航 → 点击 submit → 填写表单 → 提交 |

### 5.2 发布器核心接口

```python
class SocialPublisher:
    """社交媒体发布器"""

    async def publish(self, content: PostContent) -> PublishResult:
        """发布内容到指定平台"""
        platform = self._get_platform(content.platform)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            await self._inject_credentials(context, platform)
            result = await platform.post(context, content)
            await browser.close()
            return result

    async def interact(self, platform: str, post_id: str) -> InteractResult:
        """与受众互动（点赞、感谢回复）"""
        ...
```

### 5.3 平台适配器

```python
class TwitterPlatform:
    """Twitter 平台适配"""

    async def post(self, context, content: PostContent) -> PublishResult:
        page = await context.new_page()
        await page.goto("https://twitter.com/compose/tweet")
        # 等待并填写内容
        await page.fill('[data-testid="tweetTextarea_0"]', content.body)
        await page.click('[data-testid="tweetButton"]')
        # 返回结果
        return PublishResult(success=True, url=...)

class RedditPlatform:
    """Reddit 平台适配"""

    async def post(self, context, content: PostContent) -> PublishResult:
        page = await context.new_page()
        await page.goto(f"https://reddit.com/{content.subreddit}/submit")
        # 填写标题、正文、选择类型
        ...

class HNPlatform:
    """Hacker News 平台适配"""

    async def post(self, context, content: PostContent) -> PublishResult:
        page = await context.new_page()
        await page.goto("https://news.ycombinator.com/submit")
        # 填写标题、URL、内容
        ...
```

## 6. 调度系统设计

### 6.1 GitHub Actions 调度策略

```yaml
name: Sales Promotion Agent
on:
  schedule:
    - cron: "0 9,17 * * *"     # Twitter: 09:00 + 17:00 (1-2/天)
    - cron: "0 10 * * 1,3,5"   # Reddit: 周一/三/五 10:00
    - cron: "0 11 * * 2"       # HN: 每周二 11:00
  workflow_dispatch:
    inputs:
      platform:
        type: choice
        options: [twitter, reddit, hn]
      action:
        type: choice
        options: [post, interact, report]
```

### 6.2 发布日历

| 时间 | 周一 | 周二 | 周三 | 周四 | 周五 | 周六 | 周日 |
|------|------|------|------|------|------|------|------|
| 09:00 | Twitter | Twitter | Twitter | Twitter | Twitter | Twitter | - |
| 10:00 | Reddit | - | Reddit | - | Reddit | - | - |
| 11:00 | - | HN | - | - | - | - | - |
| 17:00 | Twitter | Twitter | Twitter | Twitter | Twitter | - | - |

### 6.3 凭据环境变量

| 变量名 | 说明 | Secret 名称 |
|--------|------|-------------|
| `TWITTER_USERNAME` | Twitter 用户名 | `TWITTER_USERNAME` |
| `TWITTER_PASSWORD` | Twitter 密码 | `TWITTER_PASSWORD` |
| `REDDIT_USERNAME` | Reddit 用户名 | `REDDIT_USERNAME` |
| `REDDIT_PASSWORD` | Reddit 密码 | `REDDIT_PASSWORD` |
| `HN_USERNAME` | HN 用户名 | `HN_USERNAME` |
| `HN_PASSWORD` | HN 密码 | `HN_PASSWORD` |

## 7. 分析追踪设计

### 7.1 数据模型

```sql
-- 发布记录表
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,          -- twitter/reddit/hn
    content_type TEXT NOT NULL,      -- tutorial/story/engagement
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    url TEXT,                        -- 发布后的 URL
   published_at DATETIME NOT NULL,
    status TEXT DEFAULT 'published', -- published/failed/draft
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 互动记录表
CREATE TABLE IF NOT EXISTS interactions (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    interaction_type TEXT NOT NULL,  -- like/reply/view
    target_id TEXT,                  -- 被互动的帖子/评论 ID
    status TEXT DEFAULT 'success',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id)
);
```

### 7.2 核心指标

| 指标 | 说明 | 计算方式 |
|------|------|----------|
| `posts_published` | 发布成功数 | COUNT posts WHERE status='published' |
| `publish_success_rate` | 发布成功率 | published / total |
| `interactions_count` | 互动次数 | COUNT interactions |
| `platform_distribution` | 平台分布 | GROUP BY platform |
| `content_type_performance` | 内容类型表现 | 按 content_type 统计 |

### 7.3 报表生成

```python
class AnalyticsTracker:
    """分析追踪器"""

    async def generate_report(self, date_range: DateRange) -> AnalyticsReport:
        """生成指定时间段的推销效果报告"""
        posts = await self._get_posts(date_range)
        interactions = await self._get_interactions(date_range)
        return AnalyticsReport(
            total_posts=len(posts),
            success_rate=self._calc_success_rate(posts),
            total_interactions=len(interactions),
            platform_breakdown=self._group_by_platform(posts),
            content_performance=self._group_by_content_type(posts),
        )
```

## 8. 安全考虑

### 8.1 凭据安全

- 所有密码通过 GitHub Secrets 注入
- 运行时通过环境变量读取，不写入代码/日志
- 日志中脱敏处理（不输出密码、Cookie）

### 8.2 反垃圾策略

- 严格遵守平台频率限制
- 内容去重（SHA-256 哈希检查）
- 随机延迟（30-120 秒）模拟人类行为
- 每个平台有独立的发布队列

### 8.3 内容安全

- LLM 生成内容通过基础过滤（无恶意链接、敏感词）
- 发布前预览模式（dry-run）支持
- 可配置的内容黑名单

## 9. 依赖项

```txt
# requirements.txt 新增
playwright>=1.40.0          # 浏览器自动化
```

安装浏览器：
```bash
playwright install chromium
```

## 10. 测试策略

### 10.1 单元测试

- `test_content_generator.py` - 内容生成逻辑
- `test_publisher.py` - 发布流程 mock 测试
- `test_analytics.py` - 分析统计逻辑
- `test_credentials.py` - 凭据管理

### 10.2 集成测试

- GitHub Actions dry-run 测试
- 平台登录流程验证（测试账号）

### 10.3 冒烟测试

```bash
# 测试内容生成
python -m monetization.sales.content_generator --dry-run --platform twitter

# 测试发布流程（不实际发布）
python -m monetization.sales.publisher --dry-run --platform twitter

# 生成报表
python -m monetization.sales.analytics --report 7d
```

---

**文档状态:** 待审核
