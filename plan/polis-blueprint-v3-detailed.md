# 🏛️ 城邦V3详细规格：互锁生命体

**版本**：V3.0  
**状态**：已实现核心框架  
**核心理念**：不做加法，做打通 — 从V2四组系统到V3互锁生命体

---

## 📋 实现总览

### 已实现的核心文件

| 文件 | 说明 | 状态 |
|------|------|------|
| `plan/polis_blueprint_v3.md` | V3蓝图总纲 | ✅ 完成 |
| `polis_interlock.py` | 互锁协议核心引擎（五层架构） | ✅ 完成 |
| `polis_v3.py` | V3主系统（社会/进化/免疫/经济/Agent） | ✅ 完成 |
| `polis_dashboard_server.py` | Dashboard服务器（已集成V3 API） | ✅ 完成 |

### V3 API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v3/stats` | GET | V3城邦总统计 |
| `/api/v3/agents` | GET | 所有Agent列表（含信誉/免疫） |
| `/api/v3/agent/{id}` | GET | 单个Agent详情 |
| `/api/v3/tick` | GET | 推进一个时间步 |
| `/api/v3/evolve` | GET | 进化一代（信誉加权繁殖） |
| `/api/v3/interlock` | GET | 互锁协议统计 |
| `/api/v3/immune` | GET | 免疫系统状态 |
| `/api/v3/social` | GET | 社会系统统计 |
| `/api/v3/market` | GET | 市场经济统计 |

---

## 🔗 互锁协议引擎（五层架构）

### L1 - 信号层：事件总线
```python
EventBus
├── subscribe(event_type, callback, system)   # 订阅事件
├── publish(event)                             # 发布事件
└── stats                                      # 事件统计
```

**核心能力**：
- 系统间异步事件通知
- 按系统/事件类型精准订阅
- 事件日志与统计
- 跨系统事件比例计算（互锁密度指标）

---

### L2 - 数据层：数据桥接
```python
DataBridge
├── register_system(name, system)        # 注册系统
├── register_converter(src, dst, func)   # 注册数据转换器
└── get_system_data(system, type, query) # 获取跨系统数据
```

**支持的数据桥接**：
- 记忆 → 社交：提取社交相关记忆
- 社交 → 进化：信誉数据转换为繁殖权重
- 免疫 → 记忆：威胁模式转换为免疫记忆
- 治理 → 社会：政策转换为社会影响因子

---

### L3 - 因果层：因果链接
```python
CausalLinkEngine
├── add_link(name, cause_sys, cause_evt, effect_sys, effect_act, condition)
├── _trigger_link(link, event)    # 触发因果
└── stats                          # 因果链接统计
```

**已实现的9条核心因果链接**：

| 名称 | 因 | 果 | 权重 |
|------|----|----|------|
| 社交记忆化 | social: social_interaction | memory: on_social_interaction | 0.8 |
| 记忆影响社交选择 | memory: memory_retrieved | social: on_memory_retrieved | 0.6 |
| 信誉提升强化记忆 | social: reputation_changed | memory: on_reputation_changed | 0.7 |
| 高信誉繁殖优势 | social: reputation_changed | evolution: on_reputation_changed | 0.9 |
| 进化影响社会结构 | evolution: evolution_tick | social: on_evolution_tick | 0.5 |
| 威胁触发免疫记忆 | immune: threat_detected | memory: on_threat_detected | 1.0 |
| 记忆加速免疫响应 | memory: memory_retrieved | immune: on_memory_retrieved | 0.9 |
| 治理决策影响社会 | governance: governance_decision | social: on_governance_decision | 0.8 |
| 社会反馈影响治理 | social: reputation_changed | governance: on_social_change | 0.6 |

---

### L4 - 闭环层：反馈回路
```python
FeedbackLoopEngine
├── create_loop(name, systems, events, loop_type, strength)
├── _detect_cycle(loop)       # 检测循环周期
├── _amplify_loop(loop)       # 放大/调节回路效应
└── stats                      # 反馈回路统计
```

**已实现的3条核心反馈回路**：

| 名称 | 类型 | 系统 | 事件链 | 强度 |
|------|------|------|--------|------|
| 信誉-进化正反馈 | 正反馈 | social → evolution | reputation_changed → evolution_tick | 0.3 |
| 记忆-免疫增强循环 | 正反馈 | memory → immune | memory_stored → immune_response | 0.5 |
| 治理-社会稳定负反馈 | 负反馈 | governance → social | governance_decision → reputation_changed | 0.4 |

---

### L5 - 共生层：系统间相互依存
*（自动涌现 - 通过L1-L4的深度联动自然产生）*

**共生指标**：
- 互锁密度 > 40%（跨系统事件/总事件）
- 至少3个活跃反馈回路
- 每个系统至少依赖2个其他系统
- 系统整体抗脆弱性（压力下能力增强）

---

## 🧩 五大系统V3增强

### 1. 🤝 社会系统 V3
**新增/增强能力**：
- ✅ 多维声誉体系（个人信誉/社会地位/影响力/可信赖度）
- ✅ 信誉传播机制（通过社交网络扩散）
- ✅ 社会阶层划分（elite/upper/middle/lower/marginal）
- ✅ 社交圈子自动形成
- ✅ 与记忆/进化/免疫的互锁接口

**社会地位计算**：
```
社会地位 = 信誉总分 × 0.6 + 社会影响力 × 0.4
```

**信誉传播**：
- 每次社交互动影响直接关系的信誉
- 通过朋友网络二级传播（衰减系数 = 关系强度 × 0.1）

---

### 2. 🧬 进化系统 V3
**新增/增强能力**：
- ✅ 免疫基因（immune_strength, stress_resistance）
- ✅ 文化基因（cultural_memes）- 知识与信念的代际传递
- ✅ 信誉加权繁殖选择
- ✅ 多维度适应度计算（健康+财富+技能+社会地位+基因质量+免疫）
- ✅ 文化知识的亲子传递

**V3繁殖评分**：
```
繁殖评分 = 基础适应度 + (信誉/100) × 0.3 + 免疫强度 × 0.2
```

**基因类型扩展**：
- 性格基因（5种）：野心、好奇心、勤奋、社交欲、风险承受
- 天赋基因（4种）：智力、社交、创造、体力
- 体质基因（2种）：精力上限、恢复速度
- **免疫基因（新增2种）**：免疫强度、压力抵抗
- **文化基因（新增）**：可传递的知识模因

---

### 3. 🛡️ 免疫系统 V3（全新系统）
**核心能力**：
- ✅ Agent健康监测与异常检测
- ✅ 威胁识别与分类（疾病/压力/行为异常/系统错误）
- ✅ 自然免疫响应（基于基因免疫强度）
- ✅ 免疫记忆（威胁模式识别加速）
- ✅ 自愈机制与治疗系统
- ✅ 社交传播模型（疾病通过互动传播）
- ✅ 系统级健康监控

**威胁类型**：
| 类型 | 来源 | 影响 |
|------|------|------|
| disease | 疾病传播 | 健康下降、精力降低 |
| stress | 心理压力 | 情绪下降、表现降低 |
| exhaustion | 过度劳累 | 精力耗尽、健康风险 |
| behavioral | 行为异常 | 社会信誉受损 |
| system | 系统错误 | 整体稳定性 |

**免疫响应流程**：
```
威胁检测 → 威胁识别 → 免疫响应 → 自愈/治疗 → 免疫记忆形成
     ↓
  事件通知 → 触发互锁 → 其他系统联动
```

---

### 4. 🏛️ 治理系统 V3
*（基于court_discussion.py增强，预留互锁接口）*

**互锁接口（已预留）**：
- `on_social_change(data)` - 社会变化影响治理决策
- `on_governance_decision(data)` - 治理决策影响社会
- 治理能力作为进化适应性指标

---

### 5. 🧠 记忆系统 V3
*（基于super_memory_engine.py增强，预留互锁接口）*

**互锁接口（已预留）**：
- `on_social_interaction(data)` - 社交互动存入记忆
- `on_reputation_changed(data)` - 信誉变化影响记忆权重
- `on_threat_detected(data)` - 威胁事件形成免疫记忆
- `on_memory_retrieved(data)` - 记忆检索加速免疫响应

---

## 🤖 V3 Agent

### 属性维度扩展
| 维度 | V2 | V3 | 说明 |
|------|-----|-----|------|
| 基础属性 | ✅ | ✅ | 精力/情绪/健康/财富 |
| 技能系统 | ✅ | ✅ | 多类别技能与经验 |
| 基因组 | ✅ | ✅+ | 新增免疫基因和文化基因 |
| 信誉系统 | 单维 | 多维 | 个人/社会/影响力/可信赖度 |
| 社会地位 | ❌ | ✅ | 五阶层划分 |
| 免疫档案 | ❌ | ✅ | 免疫强度/压力/病史 |

### 适应度计算（V3）
```python
fitness = 
  (health/100) × 0.15 +          # 健康
  (energy/max_energy) × 0.05 +   # 精力
  (mood/100) × 0.05 +            # 情绪
  min(wealth/500, 1) × 0.15 +    # 财富
  (avg_skill/50) × 0.15 +         # 技能
  genome_fitness × 0.15 +         # 基因质量
  (reputation/100) × 0.15 +       # 社会信誉
  social_status_score × 0.1       # 社会地位
```

---

## 📊 关键指标与成功度量

### 系统级指标
| 指标 | 目标 | 当前实现 |
|------|------|----------|
| 互锁密度 | > 40% | ✅ 可测量（事件总线统计） |
| 自稳能力 | 扰动恢复 < 基准50% | 🔄 需长期观测 |
| 进化效率 | > V2的1.5倍 | 🔄 需对比测试 |
| 抗脆弱性 | 压力下能力增强 | 🔄 需压力测试 |

### Agent级指标
| 指标 | 目标 | 当前实现 |
|------|------|----------|
| 记忆利用率 | > 60% | 🔄 需记忆系统完全集成 |
| 社会嵌入度 | > 5个有效连接 | ✅ 可测量 |
| 信誉区分度 | 标准差 > 15 | ✅ 可测量 |
| 免疫响应速度 | < 3个tick | ✅ 实时响应 |

---

## 🗺️ 12周路线图（当前进度）

### ✅ W1-3：记忆驱动（基础框架）
- ✅ 超级记忆引擎基础能力（已有）
- ✅ 互锁协议核心引擎（L1-L4）
- ✅ 社会系统与信誉体系
- ✅ 免疫系统基础框架
- ✅ 进化系统V3增强
- 🔄 记忆系统完全互锁（接口预留）

### ⏳ W4-6：协作驱动
- 社会网络深度建模（部分完成）
- 协作机制与记忆联动
- 群体智慧涌现
- 治理系统深度集成

### ⏳ W7-9：繁殖闭环
- 有性繁殖机制完善（部分完成）
- 基因-文化协同进化（部分完成）
- 信誉影响繁殖权重（已实现）
- 种群动态平衡

### ⏳ W10-12：民主+免疫
- 民主决策机制
- 免疫系统完善（基础已完成）
- 异常检测与自愈
- 系统整体抗脆弱性

---

## 🚀 快速开始

### 初始化V3城邦
```python
from polis_v3 import PolisV3, AgentRole

# 创建城邦
polis = PolisV3()

# 填充初始人口
polis.populate(10)

# 运行时间步
for i in range(100):
    polis.tick()

# 进化一代
result = polis.evolve_generation()

# 查看统计
stats = polis.get_polis_stats()
```

### 通过API访问
```bash
# 获取V3总览
curl http://127.0.0.1:8016/api/v3/stats

# 查看Agent列表
curl http://127.0.0.1:8016/api/v3/agents

# 推进时间步
curl http://127.0.0.1:8016/api/v3/tick

# 进化一代
curl http://127.0.0.1:8016/api/v3/evolve

# 查看互锁协议状态
curl http://127.0.0.1:8016/api/v3/interlock

# 查看免疫系统
curl http://127.0.0.1:8016/api/v3/immune
```

---

## 🔮 未来扩展方向

1. **记忆系统深度集成**：将super_memory_engine.py完全接入互锁协议
2. **治理系统增强**：朝堂议政与社会/经济系统深度联动
3. **经济系统升级**：货币体系、税收、公共服务
4. **多城邦交互**：城邦间外交、贸易、战争
5. **可视化增强**：Dashboard新增V3专属界面
