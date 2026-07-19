# Agent-Platform 60 天攻坚计划

## 差距探查结论

### 项目真实状态
- **现有能力**：322 测试通过、LiveKit 实时层接入、仿真引擎（DES tick 分发 + LLM 编排）、社区/经济/治理/进化/自治/联邦 6 大模块实现
- **诚实评分**：架构成熟度 ~75%，代码完成度 ~70%，模块融合度 ~55%，生产就绪度 ~40%

### 真实差距（按严重程度排序）

| # | 差距 | 严重度 | 影响 |
|---|------|--------|------|
| 1 | 仿真记忆无 Postgres 持久化，进程丢失即丢 | 🔴 高 | 城镇仿真无法长期运行 |
| 2 | 社区→仿真 seed 单射，无双向状态同步 | 🔴 高 | 城镇与平台割裂 |
| 3 | 经济↔治理事件桥接缺失（stake/vote 不联动） | 🔴 高 | 城邦治理空心化 |
| 4 | FederationService.fetchAgentCard 未做签名验证 | 🟡 中 | 联邦信任链不完整 |
| 5 | AutonomyPlanner 与 Guard/PolicyEngine 未集成 | 🟡 中 | 自主决策无护栏 |
| 6 | LLMProvider 错误重试无指数退避 | 🟡 中 | 瞬态故障恢复弱 |
| 7 | SimulationEngine 回退决策未广播叙事事件 | 🟡 中 | 可观测性缺口 |
| 8 | RealtimeLayer Session 恢复后媒体管道断裂 | 🟡 中 | 断线重连不完整 |
| 9 | 进化层 Skills 升级未反馈循环到 Dispatcher | 🟢 低 | 学习闭环不完整 |
| 10 | 控制台视图无实时推送（纯轮询） | 🟢 低 | 操作体验滞后 |

---

## Phase 1 (Day 1-10): 仿真引擎完善 + 记忆系统 Postgres 持久化

### Day 1-2: 记忆持久化仓储接口
**目标**：新增 `SimulationMemoryRepository` 接口（in-memory 实现已存在，补 Postgres 实现）

文件：
- 新增 `src/repository/simulation-memory/postgres.ts`
- 修改 `src/repository/simulation-memory/interface.ts`（已存在则审校）
- 新增 `src/repository/simulation-memory/inmemory.ts`（如缺失）
- 新增 `__tests__/repository/simulation-memory.test.ts`

关键设计：
- 接口方法：`save(item)`, `get residentMemories(id)`, `search(query)`, `decayAll(rate)`, `summarize(residentId)`
- Postgres 表：`simulation_memory` (id, resident_id, content, kind, importance, embedding vector, created_tick, version)
- 支持 pgvector 或 JSON 降级

### Day 3-4: SimulationEngine 接入持久化
**目标**：引擎启动时从仓储加载记忆，tick 后增量写回仓储

文件：
- 修改 `src/server/simulation/engine.ts`
- 修改 `src/server/simulation/service.ts`
- 新增 `__tests__/simulation/memory-persistence.test.ts`

关键修改：
- 构造函数增加 `memoryRepo?: SimulationMemoryRepository` 参数
- `addResident` 异步加载该居民历史记忆进 MemoryStream
- `executeTick` 完成后，将新产生的记忆 save 到仓储
- 启动/停止事件通过 `onEvent` 广播

### Day 5-6: 双向社区↔仿真同步
**目标**：seedFromCommunity 之后，仿真状态变更能回流到 CommunityService

文件：
- 修改 `src/server/simulation/seed.ts`
- 新增 `src/server/simulation/sync-back.ts`
- 修改 `src/server/simulations/service.ts`
- 新增 `__tests__/simulation/community-sync.test.ts`

关键设计：
- 定义 `SimulationSyncEvent` 类型（residentId, coinsDelta, actionType, tick）
- 经济回流：仿真授予 coins → 调用 `economyService.grant()`
- 社会关系回流：仿真中关系变化 → 更新 `CommunityResident.relationships`
- 事件桥接：通过 EventBus（DistributedEventBus）发布

### Day 7-8: 叙事事件完善
**目标**：回退决策、LLM 故障、记忆反思均产生叙事事件

文件：
- 修改 `src/server/simulation/engine.ts`
- 修改 `src/server/simulation/memory/memory-stream.ts`
- 修改 `src/server/simulation/memory/reflection.ts`
- 新增 `__tests__/simulation/narrative-events.test.ts`

关键事件类型：
- `narrative.fallback`：含 residentId、reason、tick
- `narrative.llm_error`：含 residentId、errorMessage
- `narrative.reflection`：含 residentId、reflection content、sourceMemoryIds
- `narrative.memory_decay`：含 residentId、decayedCount

### Day 9-10: Phase 1 集成测试 + 修复
**目标**：端到端验证仿真引擎持久化 + 社区同步链路完整

测试场景：
1. 创建仿真 → seed 10 居民 → 运行 50 tick → 重启引擎 → 记忆从仓储恢复
2. 仿真中居民 earning coins → 在 CommunityService 余额同步
3. LLM 不可用 → 回退决策 → 叙事事件触发 → 检索到事件记录

---

## Phase 2 (Day 11-20): 城邦经济-治理-社区三模块融合

### Day 11-12: 经济↔治理 Stake → Vote 权重联动
**目标**：居民 stake 后其投票权重按 stake 量加权

文件：
- 修改 `src/economy/service.ts`（增加 `getStakeWeight`）
- 修改 `src/governance/service.ts`（投票时查询经济 stake）
- 新增 `__tests__/integration/economy-governance.test.ts`

### Day 13-14: 治理执行经济挂钩
**目标**：提案执行时按需调用 economyService 转账或质押

文件：
- 修改 `src/governance/service.ts`
- 修改 `src/economy/service.ts`
- 新增 `__tests__/integration/proposal-execution.test.ts`

### Day 15-16: 社区声誉系统 ↔ 经济信用联动
**目标**：声誉低的居民借贷额度受限

文件：
- 修改 `src/community/service.ts`（增加 `reputation` 字段和更新逻辑）
- 修改 `src/economy/service.ts`（增加 `creditLimitByReputation`）
- 新增 `__tests__/integration/reputation-credit.test.ts`

### Day 17-18: 城邦事件总线优化
**目标**：跨模块事件订阅从同步回调改为 EventBus 发布订阅

文件：
- 修改 `src/economy/service.ts`
- 修改 `src/governance/service.ts`
- 修改 `src/community/service.ts`
- 修改 `src/events/service.ts`
- 新增 `__tests__/integration/city-state-events.test.ts`

### Day 19-20: Phase 2 集成测试 + 修复
**目标**：完整城邦场景端到端测试

测试场景：
1. 居民 A 有 100 stake → 提案投票 → 票权重 = 100 / total
2. 提案"社区奖励 50 coins 给 A" → 执行 → A 余额 +50
3. 声誉 30 的居民借贷 → 额度 = base * (reputation / 100)

---

## Phase 3 (Day 21-30): 自治规划器完善 + 联邦协议实现

### Day 21-22: AutonomyPlanner → PolicyEngine 集成
**目标**：Planner 每步决策前经护栏校验

文件：
- 修改 `src/autonomy/planner.ts`
- 修改 `src/autonomy/service.ts`
- 新增 `__tests__/autonomy/planner-guard.test.ts`

### Day 23-24: 联邦签名验证 + 端点健康检查
**目标**：fetchAgentCard 验证返回的 agentCard 签名

文件：
- 修改 `src/federation/service.ts`
- 新增 `src/federation/verify.ts`（签名验证工具）
- 新增 `__tests__/federation/signature.test.ts`

### Day 25-26: 联邦委托记录可审计
**目标**：每次委托调用记录 inputHash/outputHash，链式可验证

文件：
- 修改 `src/federation/service.ts`
- 新增 `__tests__/federation/delegation-audit.test.ts`

### Day 27-28: AutonomyService → EvolutionService 反馈环
**目标**：规划器完成的任务沉淀为进化层 Skills 经验

文件：
- 修改 `src/autonomy/service.ts`
- 修改 `src/evolution/service.ts`
- 新增 `__tests__/integration/autonomy-evolution.test.ts`

### Day 29-30: Phase 3 集成测试 + 修复

---

## Phase 4 (Day 31-40): 实时层完善 + 多模态融合

### Day 31-32: 断线重连媒体管道恢复
**目标**：Session 重连后，AI Pipeline 媒体上下文（VAD 状态、对话历史）恢复

文件：
- 修改 `src/realtime/session-manager.ts`
- 修改 `src/realtime/integration.ts`
- 新增 `__tests__/realtime/reconnect-pipeline.test.ts`

### Day 33-34: VLM 视觉帧注入 LiveKit
**目标**：浏览器端摄像头帧 → VLM → 实时字幕/描述注入房间

文件：
- 修改 `src/realtime/vlm-processor.ts`
- 修改 `src/realtime/livekit-adapter.ts`
- 新增 `__tests__/realtime/vlm-injection.test.ts`

### Day 35-36: 实时层错误重试指数退避
**目标**：STT/TTS/LLM 调用失败时按 2^n 退避重试

文件：
- 修改 `src/realtime/livekit-adapter.ts`
- 新增 `src/realtime/retry.ts`
- 新增 `__tests__/realtime/retry.test.ts`

### Day 37-38: 实时层与城邦事件桥接
**目标**：实时会话中的关键事件（如用户确认）发布到城邦 EventBus

文件：
- 修改 `src/realtime/integration.ts`
- 新增 `__tests__/integration/realtime-city-events.test.ts`

### Day 39-40: Phase 4 集成测试 + 修复

---

## Phase 5 (Day 41-50): 安全护栏 + 性能优化 + 可观测性

### Day 41-42: 三层护栏端到端测试
**目标**：L1 输入 PII 脱敏、L2 工具 SSRF 拦截、L3 输出大小限制

文件：
- 修改 `src/guard/policy-engine.ts`（补充边界用例）
- 新增 `__tests__/security/guard-e2e.test.ts`

### Day 43-44: 调度器并发性能优化
**目标**：pump 批量派发时减少 DB 往返（批量 claim + 批量状态更新）

文件：
- 修改 `src/scheduler/dispatcher.ts`
- 修改 `src/repository/queue/`（增加 batchClaim）
- 新增 `__tests__/performance/dispatcher-throughput.test.ts`

### Day 45-46: 可观测性：Trace → OpenTelemetry 格式导出
**目标**：现有 TraceRepo 增加 OTLP 格式导出端点

文件：
- 修改 `src/server/routes/system.ts`（增加 /metrics 和 /trace/export）
- 新增 `__tests__/observability/otel.test.ts`

### Day 47-48: 预算硬停 + 熔断器联动
**目标**：BudgetConfig.hardStop=true 时，Dispatcher 对该 Agent 暂停派发

文件：
- 修改 `src/scheduler/dispatcher.ts`
- 修改 `src/guard/policy-engine.ts`
- 新增 `__tests__/integration/budget-circuit-breaker.test.ts`

### Day 49-50: Phase 5 集成测试 + 修复

---

## Phase 6 (Day 51-60): 端到端集成测试 + 文档 + 部署

### Day 51-53: 全链路 E2E 测试
**目标**：覆盖 10 个核心用户旅程

测试场景：
1. 用户注册 → 接入 Agent → 下发任务 → 完成 → 进化层学习
2. 社区 stake → 治理提案 → 投票 → 执行 → 经济转账
3. 仿真 seed → 运行 100 tick → 叙事事件 → 控制台实时查看
4. 联邦注册 → 委托调用 → 审计记录
5. 实时会话 → 断线 → 重连 → 媒体恢复
6. 自治规划 → 护栏拦截 → 回退 → 叙事事件
7. 预算超限 → 熔断 → 恢复
8. PII 输入 → 脱敏 → 日志无泄漏
9. 记忆持久化 → 重启 → 恢复
10. 控制台 SSE → 实时推送

### Day 54-56: OpenAPI 文档完善
**目标**：所有路由的 OpenAPI 注释补全，生成 swagger.json

文件：
- 修改 `src/server/routes/*.ts`（补全 schema 描述）
- 修改 `src/server/openapi.ts`

### Day 57-58: 部署配置
**目标**：Dockerfile + docker-compose（含 Postgres + Redis + MediaMTX）

文件：
- 新增 `Dockerfile`
- 新增 `docker-compose.yml`
- 新增 `.dockerignore`

### Day 59-60: 最终回归 + 交付
**目标**：全量测试通过、TypeScript 编译零错误、代码无 TODO/FIXME

验证清单：
- [ ] `npm test` 全量通过
- [ ] `npx tsc --noEmit` 零错误
- [ ] 无遗留 `throw new Error('not implemented')`
- [ ] 所有新模块有对应测试
- [ ] 文档与代码一致
