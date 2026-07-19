"""
🌍 城邦生态扩展包 (Polis Ecosystem Extension)
==============================================

为城邦生态添加六大新系统：
- 环境系统 (Environment System) - 借鉴 Sugarscape 的资源-智能体交互
- 时间系统 (Temporal System)    - 借鉴季节周期和昼夜循环
- 事件系统 (Event System)        - 借鉴突发事件和危机模型
- 自驱动系统 (Autonomous Drive)  - 解决Agent无任务时"死掉"的问题
- 进化系统 (Evolution System)    - 认知进化 + 基因遗传 + 知识继承
- 复杂度系统 (Complexity System) - 技能树 + L0→L5超级智能体阶梯

设计原则：
- 不修改 polis_v3.py 核心代码
- 独立数据库（避免锁冲突）
- WAL + busy_timeout（与项目一致）
- 单连接架构

快速使用：
    from ecosystem import create_ecosystem_suite
    suite = create_ecosystem_suite()
    suite.run(days=30, verbose=True)
    print(suite.get_stats())
    suite.close()
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

from .environment import (
    EnvironmentSystem,
    EnvironmentDB,
    ResourceType,
    TerrainType,
    Season,
    RESOURCE_CONFIG,
    SEASON_EFFECTS,
    Region,
    ResourceTransaction,
    create_default_environment,
)
from .temporal import (
    TemporalSystem,
    TemporalDB,
    TimeOfDay,
    Era,
    TIME_OF_DAY_EFFECTS,
    CalendarEntry,
    create_default_temporal,
)
from .events import (
    EventSystem,
    EventsDB,
    EventCategory,
    EventSeverity,
    EVENT_TEMPLATES,
    EcosystemEvent,
    create_default_events,
)
from .interlocks import (
    InterlockBus,
    InterlockEvent,
    InterlockEventType,
    EcosystemSuite,
    create_ecosystem_suite,
)
from .autonomous import (
    AutonomousDriveSystem,
    AutonomousDB,
    MotivationType,
    ActionType,
    AgentMotivation,
    AutonomousAction,
    create_default_autonomous,
)
from .evolution import (
    EvolutionEngine,
    EvolutionDB,
    CognitiveGenome,
    CognitiveTrait,
    ComplexityLevel,
    GenerationRecord,
    create_default_evolution,
)
from .complexity import (
    ComplexityEngine,
    ComplexityDB,
    ComplexityProfile,
    SkillMastery,
    SkillType,
    create_default_complexity,
)

__all__ = [
    # Environment
    "EnvironmentSystem", "EnvironmentDB", "ResourceType",
    "TerrainType", "Season", "RESOURCE_CONFIG", "SEASON_EFFECTS",
    "Region", "ResourceTransaction", "create_default_environment",
    # Temporal
    "TemporalSystem", "TemporalDB", "TimeOfDay", "Era",
    "CalendarEntry", "TIME_OF_DAY_EFFECTS", "create_default_temporal",
    # Events
    "EventSystem", "EventsDB", "EventCategory", "EventSeverity",
    "EVENT_TEMPLATES", "EcosystemEvent", "create_default_events",
    # Interlocks
    "InterlockBus", "InterlockEvent", "InterlockEventType",
    "EcosystemSuite", "create_ecosystem_suite",
    # Autonomous
    "AutonomousDriveSystem", "AutonomousDB", "MotivationType",
    "ActionType", "AgentMotivation", "AutonomousAction",
    "create_default_autonomous",
    # Evolution
    "EvolutionEngine", "EvolutionDB", "CognitiveGenome",
    "CognitiveTrait", "ComplexityLevel", "GenerationRecord",
    "create_default_evolution",
    # Complexity
    "ComplexityEngine", "ComplexityDB", "ComplexityProfile",
    "SkillMastery", "SkillType", "create_default_complexity",
]

__version__ = "1.0.0"
