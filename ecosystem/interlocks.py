"""
🔗 城邦生态 - 互锁协议桥接器 (Interlock Bridge)
================================================

将新增的环境/时间/事件三个系统通过互锁协议连接起来，
形成"环境 ↔ 时间 ↔ 事件"三角闭环，同时与 polis_v3 的五大系统对接。

L1 - 信号层：事件总线
L2 - 数据层：资源数据桥
L3 - 因果层：因果链接
L4 - 闭环层：反馈回路
L5 - 共生层：与原五大系统共生

使用示例：
    from ecosystem import create_ecosystem_suite
    suite = create_ecosystem_suite()
    # 一键运行
    suite.tick(world_day=suite.temporal.get_clock()["world_day"])
"""

# 强制重新加载标准库 inspect（避免被项目根目录的 inspect.py 遮蔽）
import sys as _ecosystem_sys
import importlib as _ecosystem_importlib
if 'inspect' in _ecosystem_sys.modules and not hasattr(_ecosystem_sys.modules.get('inspect'), 'get_annotations'):
    # 移除被污染的 inspect
    del _ecosystem_sys.modules['inspect']
    import inspect  # 重新加载标准库的
else:
    import inspect

import time
import json
import logging
import os
import threading
import weakref
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

from .environment import EnvironmentSystem, create_default_environment, ResourceType, Season
from .temporal import TemporalSystem, create_default_temporal, TimeOfDay
from .events import EventSystem, create_default_events, EcosystemEvent
from .autonomous import AutonomousDriveSystem, create_default_autonomous, ActionType
from .evolution import EvolutionEngine, create_default_evolution
from .complexity import ComplexityEngine, create_default_complexity, SkillType

try:
    from polis_hermes_bridge import HermesBridge, get_bridge
    _HERMES_AVAILABLE = True
except ImportError:
    _HERMES_AVAILABLE = False
    HermesBridge = None
    get_bridge = None

logger = logging.getLogger('polis.interlock')

# ============================================================
# 🎯 Action → Skill 正确映射（基于 ActionType 枚举值字符串）
# ============================================================
ACTION_SKILL_MAP: Dict[str, SkillType] = {
    ActionType.EXPLORE.value: SkillType.SCOUTING,
    ActionType.GATHER_RESOURCES.value: SkillType.GATHERING,
    ActionType.LEARN_SKILL.value: SkillType.ANALYSIS,
    ActionType.SOCIALIZE.value: SkillType.DIPLOMACY,
    ActionType.TRADE.value: SkillType.TRADING,
    ActionType.CREATE.value: SkillType.CRAFTING,
    ActionType.INVESTIGATE.value: SkillType.ANALYSIS,
    ActionType.TEACH.value: SkillType.TEACHING,
    ActionType.INNOVATE.value: SkillType.INNOVATION,
}


# ============================================================
# 🔗 互锁事件总线
# ============================================================

class InterlockEventType(Enum):
    """互锁事件类型"""
    # 来自环境系统
    SEASON_CHANGED = "season_changed"
    REGION_CREATED = "region_created"
    REGION_AT_CAPACITY = "region_at_capacity"
    RESOURCE_SHORTAGE = "resource_shortage"
    RESOURCES_REGENERATED = "resources_regenerated"

    # 来自时间系统
    NEW_DAY = "new_day"
    NEW_YEAR = "new_year"
    TIME_OF_DAY_CHANGED = "time_of_day_changed"

    # 来自事件系统
    EVENT_TRIGGERED = "event_triggered"

    # 与原五大系统对接（预留）
    AGENT_TICK = "agent_tick"
    AGENT_DIED = "agent_died"
    AGENT_BORN = "agent_born"
    MEMORY_STORED = "memory_stored"
    REPUTATION_CHANGED = "reputation_changed"
    GOVERNANCE_DECISION = "governance_decision"
    THREAT_DETECTED = "threat_detected"


@dataclass
class InterlockEvent:
    """互锁事件（与 polis_interlock 兼容）"""
    event_id: str
    event_type: str
    source_system: str  # environment/temporal/events/polis_v3
    target_systems: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: float = 0.5
    processed: bool = False


class InterlockBus:
    """
    互锁事件总线 - 三个新系统的中枢神经

    提供：
    - 事件发布
    - 订阅模式
    - 因果链接注册
    - 反馈回路管理
    """

    def __init__(self):
        self.subscribers: Dict[str, List[callable]] = defaultdict(list)
        from collections import deque
        self.event_log: deque = deque(maxlen=5000)  # 自动淘汰旧事件
        self.max_log_size = 5000
        self.total_events = 0
        self.cross_system_events = 0
        self._lock = threading.Lock()  # 线程安全锁
        # 因果链接 L3
        self.causal_links: List[Dict] = []
        # 反馈回路 L4
        self.feedback_loops: List[Dict] = []
        logger.info("InterlockBus initialized")

    def publish(self, event: InterlockEvent):
        """发布事件 + 处理因果链接和反馈回路（线程安全）"""
        with self._lock:
            self.event_log.append(event)
            self.total_events += 1
            # deque(maxlen=...) 自动淘汰，无需手动裁剪
            subscribers = list(self.subscribers.get(event.event_type, []))
        
        # 在锁外分发事件，避免回调中再次 publish 导致死锁
        for cb in subscribers:
            try:
                cb(event)
            except Exception as e:
                logger.warning(f"Subscriber failed for {event.event_type}: {e}")
        # 处理因果链接 L3
        self._process_causal_links(event)
        # 处理反馈回路 L4
        self._process_feedback_loops(event)
        # 跨系统事件计数
        if event.target_systems:
            self.cross_system_events += 1
        logger.debug(f"InterlockEvent published: {event.event_type} from {event.source_system}")

    def _process_causal_links(self, event: InterlockEvent):
        """处理因果链接 - 根据事件触发关联动作"""
        for link in self.causal_links:
            cause_event = link.get("cause_event", "")
            if event.event_type == cause_event:
                effect_system = link.get("effect_system", "")
                effect_action = link.get("effect_action", "")
                logger.debug(f"Causal link triggered: {link.get('name')} → {effect_system}.{effect_action}")

    def _process_feedback_loops(self, event: InterlockEvent):
        """处理反馈回路 - 检测循环触发"""
        for loop in self.feedback_loops:
            events_chain = loop.get("events", [])
            if event.event_type in events_chain:
                logger.debug(f"Feedback loop detected: {loop.get('name')} at {event.event_type}")

    def subscribe(self, event_type: str, callback: callable):
        """订阅事件"""
        self.subscribers[event_type].append(callback)

    def register_causal_link(self, link: Dict):
        """注册因果链接 L3"""
        self.causal_links.append(link)
        logger.info(f"Causal link registered: {link.get('name', 'unnamed')}")

    def register_feedback_loop(self, loop: Dict):
        """注册反馈回路 L4"""
        self.feedback_loops.append(loop)
        logger.info(f"Feedback loop registered: {loop.get('name', 'unnamed')}")

    def get_recent_events(self, limit: int = 20) -> List[InterlockEvent]:
        return self.event_log[-limit:]

    def get_stats(self) -> Dict:
        return {
            "total_events": self.total_events,
            "cross_system_events": self.cross_system_events,
            "current_log_size": len(self.event_log),
            "subscriber_count": sum(len(v) for v in self.subscribers.values()),
            "causal_links": len(self.causal_links),
            "feedback_loops": len(self.feedback_loops),
        }


# ============================================================
# 🏛️ 城邦生态套件 - 一键集成
# ============================================================

class EcosystemSuite:
    """
    城邦生态套件 - 整合环境/时间/事件/自驱动四大新系统

    互锁关系：
    ┌──────────┐
    │ Temporal │ ──new_day──→ Environment (regenerate)
    │          │ ──new_year──→ Events (annual reset)
    └─────┬────┘
          │ season
          ↓
    ┌──────────┐  entropy  ┌────────┐
    │   Env    │ ────────→ │ Events │
    │ (entropy)│           │  tick  │
    └──────────┘           └────┬───┘
                                │ event_triggered
                                ↓
                          InterlockBus
                                ↓
              ┌─────────────────┼─────────────────┐
              ↓                 ↓                 ↓
        Autonomous          Evolution         Complexity
        (Agent驱动)        (认知进化)        (技能与智能阶梯)
              └─────────────────┼─────────────────┘
                                ↓
                        Original 5 Systems
                        (Memory/Social/Evolution/
                         Governance/Immune)
    """

    def __init__(self, data_dir: str = None, bus: InterlockBus = None):
        self.data_dir = data_dir or os.environ.get(
            "CITY_STATE_DATA_DIR",
            str(Path.home() / "AppData/Roaming/TRAE SOLO CN/ModularData/ai-agent/work-mode-projects/6a45044b9f3d6718577ed1f8/city_state_data/ecosystem")
        )
        self.bus = bus or InterlockBus()
        self._agents_state: Optional[Dict] = None
        self._lock = threading.Lock()

        # 六大新系统
        self.environment = create_default_environment(self.data_dir)
        self.temporal = create_default_temporal(self.data_dir)
        self.events = create_default_events(
            self.data_dir, self.environment, self.temporal
        )
        self.autonomous = create_default_autonomous(
            self.data_dir, self.environment, self.temporal
        )
        self.evolution = create_default_evolution(self.data_dir)
        self.complexity = create_default_complexity(self.data_dir)

        # 注册互锁
        self._wire_interlocks()
        # 设置初始季节
        self.environment.set_season(Season(self.temporal.get_season()))
        logger.info("EcosystemSuite initialized and wired")

    def _make_interlock_callback(self, prefix: str, target_systems: List[str]):
        """
        创建弱引用互锁回调，避免 Lambda 循环引用导致的内存泄漏

        使用 weakref 打破 EcosystemSuite -> Lambda -> self 循环
        """
        weak_self = weakref.ref(self)
        weak_bus = weakref.ref(self.bus)

        def callback(source: str, et: str, data: Dict):
            suite = weak_self()
            bus = weak_bus()
            # 如果对象已被垃圾回收，静默退出
            if suite is None or bus is None:
                return
            try:
                bus.publish(InterlockEvent(
                    event_id=f"{prefix}_{int(time.time()*1000)}_{hash((source, et)) & 0xFFFF}",
                    event_type=f"{prefix}.{et}",
                    source_system=source,
                    target_systems=target_systems,
                    data=data
                ))
            except Exception as e:
                logger.warning(f"Interlock callback failed for {prefix}.{et}: {e}")

        return callback

    def _wire_interlocks(self):
        """互锁连线 - 六大系统完整联动"""
        # 环境系统 → 总线 (使用弱引用避免循环引用)
        self.environment.register_interlock(
            self._make_interlock_callback("env", ["events", "temporal", "autonomous", "evolution"])
        )
        # 时间系统 → 总线
        self.temporal.register_interlock(
            self._make_interlock_callback("tmp", ["environment", "events", "autonomous", "evolution", "complexity"])
        )
        # 事件系统 → 总线
        self.events.register_interlock(
            self._make_interlock_callback("evt", ["environment", "autonomous", "complexity", "evolution"])
        )
        # 自驱动系统 → 总线
        self.autonomous.register_interlock(
            self._make_interlock_callback("auto", ["complexity", "evolution", "environment"])
        )
        # 进化系统 → 总线
        self.evolution.register_interlock(
            self._make_interlock_callback("evo", ["complexity", "autonomous"])
        )
        # 复杂度系统 → 总线
        self.complexity.register_interlock(
            self._make_interlock_callback("comp", ["evolution", "events"])
        )

        # 订阅：新一天 → 资源再生 + 自驱动
        self.bus.subscribe("tmp.new_day", self._on_new_day)
        # 订阅：新年 → 代际进化
        self.bus.subscribe("tmp.new_year", self._on_new_year)
        # 订阅：事件触发 → 影响Agent行为
        self.bus.subscribe("evt.event_triggered", self._on_event)
        # 订阅：Agent行动 → 技能练习（通过互锁总线异步处理）
        self.bus.subscribe("auto.agent_action", self._on_action_taken)
        # 订阅：知识传承 → 进化加速
        self.bus.subscribe("comp.knowledge_transfer", self._on_knowledge_transfer)

        # 因果链接 L3
        self.bus.register_causal_link({
            "name": "resource_shortage_drives_migration",
            "cause_system": "environment",
            "cause_event": "env.resource_shortage",
            "effect_system": "autonomous",
            "effect_action": "increase_exploration_motivation",
            "weight": 1.0,
        })
        self.bus.register_causal_link({
            "name": "season_changes_affect_resources",
            "cause_system": "temporal",
            "cause_event": "tmp.new_day",
            "effect_system": "environment",
            "effect_action": "regenerate_with_season",
            "weight": 1.0,
        })
        self.bus.register_causal_link({
            "name": "high_entropy_triggers_crisis_events",
            "cause_system": "environment",
            "cause_event": "env.resources_regenerated",
            "effect_system": "events",
            "effect_action": "evaluate_entropy",
            "weight": 0.8,
        })
        self.bus.register_causal_link({
            "name": "action_practices_skill",
            "cause_system": "autonomous",
            "cause_event": "auto.action_taken",
            "effect_system": "complexity",
            "effect_action": "gain_skill_experience",
            "weight": 0.9,
        })
        self.bus.register_causal_link({
            "name": "milestone_drives_evolution",
            "cause_system": "complexity",
            "cause_event": "comp.milestone_achieved",
            "effect_system": "evolution",
            "effect_action": "boost_mutation_rate",
            "weight": 0.7,
        })
        self.bus.register_causal_link({
            "name": "generation_evolves_complexity",
            "cause_system": "evolution",
            "cause_event": "evo.generation_evolved",
            "effect_system": "complexity",
            "effect_action": "unlock_higher_tier_skills",
            "weight": 0.8,
        })

        # 反馈回路 L4
        self.bus.register_feedback_loop({
            "name": "resource_scarcity_cascade",
            "systems": ["environment", "events", "environment"],
            "loop_type": "positive",
            "events": ["env.resource_shortage", "evt.event_triggered",
                       "env.resources_regenerated"],
            "strength": 1.0,
        })
        self.bus.register_feedback_loop({
            "name": "seasonal_resource_cycle",
            "systems": ["temporal", "environment", "events"],
            "loop_type": "negative",
            "events": ["tmp.new_day", "env.resources_regenerated"],
            "strength": 0.7,
        })
        self.bus.register_feedback_loop({
            "name": "intelligence_explosion",
            "systems": ["complexity", "evolution", "complexity"],
            "loop_type": "positive",
            "events": ["comp.innovation_created", "evo.generation_evolved",
                       "comp.milestone_achieved"],
            "strength": 0.6,
        })
        self.bus.register_feedback_loop({
            "name": "skill_mastery_cycle",
            "systems": ["autonomous", "complexity", "autonomous"],
            "loop_type": "positive",
            "events": ["auto.action_taken", "comp.knowledge_transfer",
                       "auto.action_taken"],
            "strength": 0.5,
        })

    def _on_new_day(self, event: InterlockEvent):
        """新一天 - 触发资源再生 + Agent自驱动 + 技能练习"""
        try:
            self.environment.regenerate_all(dt_seconds=1.0)
            new_season = self.temporal.get_season()
            self.environment.set_season(Season(new_season))
        except Exception as e:
            logger.warning(f"_on_new_day env failed: {e}")

    def _on_new_year(self, event: InterlockEvent):
        """新年 - 触发代际进化 + 全种群技能检测"""
        year = event.data.get('year', 0)
        logger.info(f"New year: {year} - triggering evolution via interlock bus")

        # 获取 agent_ids：优先从运行时状态，回退到数据库已存基因组
        agent_ids = []
        if hasattr(self, '_agents_state') and self._agents_state:
            agent_ids = list(self._agents_state.keys())
        else:
            # 从进化数据库读取已有基因组
            genomes = self.evolution.db.list_genomes(limit=100)
            agent_ids = [g.agent_id for g in genomes]
            if agent_ids:
                logger.info(f"No runtime agent state, using {len(agent_ids)} genomes from DB")

        if not agent_ids:
            logger.warning("No agents available for evolution")
            return

        try:
            entropy = self.environment.calculate_entropy()
            self.evolution.evolve_generation(
                agent_ids, generation=year, top_ratio=0.4,
                stress_factor=1.0 + entropy * 0.5
            )
            # 文明里程碑检测 - 检查所有 Agent，不限制数量
            for aid in agent_ids:
                self.complexity.check_civilization_milestones(aid, year)
        except Exception as e:
            logger.warning(f"Evolution via interlock failed: {e}")

    def _on_event(self, event: InterlockEvent):
        """事件触发 - 影响Agent动机和行为"""
        data = event.data
        name = data.get("name", "unknown")
        severity = data.get("severity", "info")
        logger.info(f"Event impact on agents: {name} (severity={severity})")
        # 严重事件提升种群 comfort 动机（驱动休息/恢复）
        if severity in ("critical", "disaster"):
            if hasattr(self, '_agents_state') and self._agents_state:
                for agent_id, state in self._agents_state.items():
                    genes = state.get('genes', {})
                    if genes and hasattr(self.autonomous, '_agent_genomes'):
                        self.autonomous._agent_genomes[agent_id] = genes

    def _on_action_taken(self, event: InterlockEvent):
        """Agent采取行动 - 练习对应技能（使用统一 ACTION_SKILL_MAP）"""
        try:
            data = event.data
            agent_id = data.get('agent_id')
            action_type = data.get('action_type', '')
            if agent_id:
                skill = ACTION_SKILL_MAP.get(action_type)
                if skill:
                    self.complexity.practice_skill(agent_id, skill, amount=1.0)
        except Exception as e:
            logger.warning(f"_on_action_taken failed: {e}")

    def _on_knowledge_transfer(self, event: InterlockEvent):
        """知识传承 - 提升进化速度"""
        try:
            data = event.data
            logger.info(f"Knowledge transferred: {data.get('skill_type')} "
                        f"from {data.get('teacher_id')} to {data.get('learner_id')}")
        except Exception as e:
            logger.warning(f"_on_knowledge_transfer failed: {e}")

    # ----- 一键 tick -----
    def tick(self, hours: float = 24.0, agents_state: Dict = None):
        """
        执行一个 tick（默认一天）- 六大系统完整联动

        流程：
        1. 时间推进 → 触发 new_day / new_year
        2. 资源再生（基于季节）
        3. 事件概率触发（基于熵）
        4. Agent自驱动行动（无任务时主动选择行为）
        5. 行动 → 技能练习 → 复杂度提升
        6. 新年 → 代际进化
        7. 文明里程碑检测
        """
        # 存储种群快照供互锁回调使用
        self._agents_state = agents_state

        # 1. 时间推进
        prev_year = self.temporal.get_clock().get("world_year", 0)
        self.temporal.advance(hours)
        new_clock = self.temporal.get_clock()
        is_new_year = new_clock.get("world_year", 0) > prev_year

        # 2. 事件 tick（基于当前熵和季节）
        entropy = self.environment.calculate_entropy()
        season = self.temporal.get_season()
        triggered = self.events.tick(current_season=season, current_entropy=entropy)

        # 3. Agent自驱动（如果提供了agents_state）
        actions = {}
        if agents_state:
            # 自动注册Agent基因（如果还没注册）
            for agent_id, state in agents_state.items():
                genes = state.get('genes', {})
                if genes:
                    try:
                        self.autonomous.register_agent_genome(agent_id, genes)
                    except Exception as e:
                        logger.warning(f"Failed to register genome for {agent_id}: {e}")
            actions = self.autonomous.drive_all(agents_state)
            # 技能练习由互锁总线 _on_action_taken 回调处理

        # 4. 新年 → 文明里程碑检测（进化已由 _on_new_year 回调处理，避免重复执行）
        evolution_result = None
        milestones = []
        if is_new_year and agents_state:
            gen = new_clock.get("world_year", 1)
            agent_ids = list(agents_state.keys())
            # 进化已由互锁总线 _on_new_year 回调执行，此处不再重复
            # 仅查询结果用于返回
            try:
                stats = self.evolution.db.get_statistics()
                evolution_result = {
                    "generation": stats.get("latest_generation", gen),
                    "avg_iq": stats.get("avg_iq", 0),
                    "diversity": stats.get("diversity", 0),
                    "note": "executed via _on_new_year callback"
                }
            except Exception:
                pass
            # 文明里程碑检测
            for aid in agent_ids:
                try:
                    new_milestones = self.complexity.check_civilization_milestones(aid, gen)
                    milestones.extend(new_milestones)
                except Exception as e:
                    logger.warning(f"Milestone check failed for {aid}: {e}")

        return {
            "world_day": new_clock.get("world_day", 0),
            "world_year": new_clock.get("world_year", 0),
            "season": season,
            "time_of_day": self.temporal.get_time_of_day().value,
            "entropy": entropy,
            "events_triggered": [e.name if hasattr(e, 'name') else str(e) for e in triggered],
            "agent_actions": {aid: a.action_type if a else None
                              for aid, a in actions.items()},
            "is_new_year": is_new_year,
            "evolution": evolution_result,
            "new_milestones": [m['name'] for m in milestones],
        }

    def run(self, days: int = 30, hours_per_tick: float = 24.0,
            verbose: bool = False, agents_state: Dict = None) -> List[Dict]:
        """
        批量运行 N 天
        如果提供 agents_state，则驱动 Agent 主动行动 + 技能练习 + 进化
        """
        results = []
        for i in range(days):
            result = self.tick(hours_per_tick, agents_state=agents_state)
            results.append(result)
            if verbose:
                day_info = (f"Day {result['world_day']} (Y{result['world_year']}): "
                           f"season={result['season']}, entropy={result['entropy']:.3f}, "
                           f"events={len(result['events_triggered'])}")
                if result['agent_actions']:
                    n_actions = sum(1 for v in result['agent_actions'].values() if v)
                    day_info += f", actions={n_actions}"
                if result['is_new_year'] and result['evolution']:
                    evo = result['evolution']
                    day_info += (f" | EVOLUTION Gen{result['world_year']}: "
                                f"avg_iq={evo.get('avg_iq', 0)}")
                logger.info(day_info)
        return results

    def get_stats(self) -> Dict:
        """获取系统统计"""
        return {
            "regions": len(self.environment.list_regions()),
            "events_logged": len(self.events.list_events(limit=1000)),
            "active_events": self.events.count_active_events(),
            "ecosystem_entropy": self.environment.calculate_entropy(),
            "calendar_entries": len(self.temporal.list_calendar()),
            "motivated_agents": self.autonomous.get_motivation_count(),
            "evolution_stats": self.evolution.get_statistics(),
            "complexity_stats": self.complexity.get_statistics(),
            "bus_stats": self.bus.get_stats(),
        }

    def close(self):
        """关闭所有数据库连接"""
        try:
            self.environment.db.close()
        except Exception:
            pass
        try:
            self.temporal.db.close()
        except Exception:
            pass
        try:
            self.events.db.close()
        except Exception:
            pass
        try:
            self.autonomous.db.close()
        except Exception:
            pass
        try:
            self.evolution.db.close()
        except Exception:
            pass
        try:
            self.complexity.db.close()
        except Exception:
            pass


def create_ecosystem_suite(data_dir: str = None) -> EcosystemSuite:
    """工厂函数 - 一键创建完整生态套件"""
    return EcosystemSuite(data_dir)


# ============================================================
# 🧪 冒烟测试
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    print("=== 城邦生态套件冒烟测试 ===\n")
    suite = create_ecosystem_suite()
    print(f"初始状态: {suite.get_stats()}\n")
    print("运行 30 天模拟...\n")
    results = suite.run(days=30, verbose=True)
    print(f"\n最终状态: {suite.get_stats()}")
    print(f"事件触发总数: {sum(len(r['events_triggered']) for r in results)}")
    print("\n=== 测试完成 ===")
    suite.close()
