"""
🎲 城邦生态 - 随机事件系统 (Random Event System)
=================================================

借鉴 Sugarscape 的突发事件机制和 Rat-Utopia 的危机模型。
为城邦生态增加系统性的随机扰动，提升生态活力和抗脆弱性测试。

核心能力：
- 自然灾害（洪水/干旱/瘟疫/地震）
- 机遇事件（资源发现/技术突破/天才诞生）
- 危机事件（叛乱/经济崩溃/信任崩塌）
- 季节性事件爆发
- 概率自适应（与生态熵关联）

设计原则：
- 独立数据库（events.db）
- 与环境系统、时间系统深度联动
- 互锁协议通知五大系统
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

import sqlite3
import time
import random
import math
import json
import logging
import os
import threading
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


logger = logging.getLogger('polis.events')


# ============================================================
# 🎯 常量定义
# ============================================================

POPULATION_IMPACT_MULTIPLIER = 10  # 人口影响转换系数


# ============================================================
# 🎯 基础定义
# ============================================================

class EventCategory(Enum):
    """事件类别"""
    NATURAL_DISASTER = "natural_disaster"
    OPPORTUNITY = "opportunity"
    CRISIS = "crisis"
    SOCIAL = "social"
    DISCOVERY = "discovery"


class EventSeverity(Enum):
    """事件严重度"""
    MINOR = "minor"        # 影响 5% 范围
    MODERATE = "moderate"  # 影响 15% 范围
    MAJOR = "major"        # 影响 30% 范围
    CATASTROPHIC = "catastrophic"  # 影响 50% 范围


# 事件模板定义
EVENT_TEMPLATES = {
    # 自然灾害（参考 Sugarscape 的环境扰动）
    "flood": {
        "category": EventCategory.NATURAL_DISASTER,
        "name": "洪水",
        "description": "河水泛滥，影响周边区域资源",
        "default_severity": EventSeverity.MODERATE,
        "base_probability": 0.01,
        "impacts": {"water": 0.5, "food": -0.3, "materials": -0.2},
        "affected_resources": ["food", "materials"],
        "season_bias": ["spring", "summer"],
    },
    "drought": {
        "category": EventCategory.NATURAL_DISASTER,
        "name": "干旱",
        "description": "持续无雨，水资源枯竭",
        "default_severity": EventSeverity.MAJOR,
        "base_probability": 0.008,
        "impacts": {"water": -0.5, "food": -0.3, "energy": -0.1},
        "affected_resources": ["water", "food"],
        "season_bias": ["summer", "autumn"],
    },
    "plague": {
        "category": EventCategory.NATURAL_DISASTER,
        "name": "瘟疫",
        "description": "疾病传播，影响 Agent 健康",
        "default_severity": EventSeverity.MAJOR,
        "base_probability": 0.005,
        "impacts": {"population": -0.05, "productivity": -0.3},
        "affected_resources": [],
        "season_bias": ["winter", "spring"],
    },
    "earthquake": {
        "category": EventCategory.NATURAL_DISASTER,
        "name": "地震",
        "description": "地质活动，破坏基础设施",
        "default_severity": EventSeverity.MODERATE,
        "base_probability": 0.003,
        "impacts": {"materials": -0.4, "energy": -0.2},
        "affected_resources": ["materials"],
        "season_bias": [],
    },

    # 机遇事件
    "resource_discovery": {
        "category": EventCategory.OPPORTUNITY,
        "name": "资源发现",
        "description": "发现新的资源富集区",
        "default_severity": EventSeverity.MINOR,
        "base_probability": 0.02,
        "impacts": {"food": 0.3, "materials": 0.3},
        "affected_resources": ["food", "materials"],
        "season_bias": [],
    },
    "immigration_wave": {
        "category": EventCategory.OPPORTUNITY,
        "name": "移民浪潮",
        "description": "周边人口涌入",
        "default_severity": EventSeverity.MODERATE,
        "base_probability": 0.015,
        "impacts": {"population": 0.1, "social": 0.2},
        "affected_resources": [],
        "season_bias": ["spring"],
    },
    "trade_caravan": {
        "category": EventCategory.OPPORTUNITY,
        "name": "贸易商队",
        "description": "远方商队带来新商品",
        "default_severity": EventSeverity.MINOR,
        "base_probability": 0.025,
        "impacts": {"materials": 0.2, "energy": 0.2},
        "affected_resources": ["materials", "energy"],
        "season_bias": ["autumn"],
    },

    # 危机事件（参考 Rat-Utopia 行为沉沦）
    "resource_crisis": {
        "category": EventCategory.CRISIS,
        "name": "资源危机",
        "description": "关键资源严重短缺",
        "default_severity": EventSeverity.MAJOR,
        "base_probability": 0.008,
        "impacts": {"trust": -0.3, "aggression": 0.4},
        "affected_resources": [],
        "season_bias": [],
        "entropy_trigger": 0.6,  # 仅当生态熵高时触发
    },
    "social_unrest": {
        "category": EventCategory.CRISIS,
        "name": "社会动荡",
        "description": "民众不满情绪上升",
        "default_severity": EventSeverity.MODERATE,
        "base_probability": 0.006,
        "impacts": {"trust": -0.4, "productivity": -0.3},
        "affected_resources": [],
        "season_bias": [],
        "entropy_trigger": 0.5,
    },
    "trust_collapse": {
        "category": EventCategory.CRISIS,
        "name": "信任崩塌",
        "description": "社会信任基础瓦解",
        "default_severity": EventSeverity.CATASTROPHIC,
        "base_probability": 0.002,
        "impacts": {"trust": -0.6, "social": -0.5},
        "affected_resources": [],
        "season_bias": [],
        "entropy_trigger": 0.7,
    },

    # 文明事件
    "cultural_revival": {
        "category": EventCategory.SOCIAL,
        "name": "文化复兴",
        "description": "传统价值观回归",
        "default_severity": EventSeverity.MINOR,
        "base_probability": 0.012,
        "impacts": {"trust": 0.2, "social": 0.3},
        "affected_resources": [],
        "season_bias": ["spring"],
    },
    "breakthrough": {
        "category": EventCategory.DISCOVERY,
        "name": "技术突破",
        "description": "关键技术被发明",
        "default_severity": EventSeverity.MODERATE,
        "base_probability": 0.01,
        "impacts": {"productivity": 0.3, "materials": 0.1},
        "affected_resources": [],
        "season_bias": [],
    },
}


# ============================================================
# 📦 数据类
# ============================================================

@dataclass
class EcosystemEvent:
    """生态事件"""
    event_id: str
    event_key: str
    name: str
    category: str
    severity: str
    region_id: str
    season: str
    world_day: int
    impacts: Dict[str, float] = field(default_factory=dict)
    description: str = ""
    resolved: bool = False
    timestamp: float = field(default_factory=time.time)
    resolved_at: float = 0.0
    effects_applied: Dict[str, float] = field(default_factory=dict)


# ============================================================
# 🗄️ 数据库层
# ============================================================

class EventsDB:
    """事件系统数据库 - 独立.db，WAL模式"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        self._conn = conn
        self._create_tables()
        logger.info(f"EventsDB initialized: {self.db_path}")

    def _create_tables(self):
        cur = self._conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ecosystem_event (
                event_id TEXT PRIMARY KEY,
                event_key TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                region_id TEXT NOT NULL,
                season TEXT NOT NULL,
                world_day INTEGER NOT NULL,
                impacts TEXT NOT NULL,
                description TEXT DEFAULT '',
                resolved INTEGER DEFAULT 0,
                timestamp REAL NOT NULL,
                resolved_at REAL DEFAULT 0,
                effects_applied TEXT DEFAULT '{}'
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ecosystem_event_region_day
                ON ecosystem_event(region_id, world_day DESC)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ecosystem_event_category
                ON ecosystem_event(category, resolved)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS event_cooldown (
                event_key TEXT PRIMARY KEY,
                last_trigger_world_day INTEGER NOT NULL,
                trigger_count INTEGER DEFAULT 0
            )
        """)
        self._conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def rollback(self):
        """回滚当前事务"""
        if self._conn:
            try:
                self._conn.rollback()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # ----- Event 操作 -----
    def insert_event(self, ev: EcosystemEvent):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO ecosystem_event
                    (event_id, event_key, name, category, severity, region_id,
                     season, world_day, impacts, description, resolved,
                     timestamp, resolved_at, effects_applied)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ev.event_id, ev.event_key, ev.name, ev.category, ev.severity,
                  ev.region_id, ev.season, ev.world_day,
                  json.dumps(ev.impacts), ev.description,
                  1 if ev.resolved else 0, ev.timestamp, ev.resolved_at,
                  json.dumps(ev.effects_applied)))
            self._conn.commit()

    def list_events(self, region_id: str = None, only_active: bool = False,
                    limit: int = 50) -> List[EcosystemEvent]:
        cur = self._conn.cursor()
        sql = "SELECT event_id, event_key, name, category, severity, region_id, season, world_day, impacts, description, resolved, timestamp, resolved_at, effects_applied FROM ecosystem_event"
        params = []
        conditions = []
        if region_id:
            conditions.append("region_id = ?")
            params.append(region_id)
        if only_active:
            conditions.append("resolved = 0")
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = cur.execute(sql, params).fetchall()
        return [self._row_to_event(r) for r in rows]

    def get_event(self, event_id: str) -> Optional[EcosystemEvent]:
        cur = self._conn.cursor()
        row = cur.execute("""
            SELECT event_id, event_key, name, category, severity, region_id, season, world_day,
                   impacts, description, resolved, timestamp, resolved_at, effects_applied
            FROM ecosystem_event WHERE event_id = ?
        """, (event_id,)).fetchone()
        return self._row_to_event(row) if row else None

    def resolve_event(self, event_id: str, effects_applied: dict = None):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("""
                UPDATE ecosystem_event
                SET resolved = 1, resolved_at = ?, effects_applied = ?
                WHERE event_id = ?
            """, (time.time(), json.dumps(effects_applied or {}), event_id))
            self._conn.commit()

    def count_active_events(self) -> int:
        cur = self._conn.cursor()
        row = cur.execute("SELECT COUNT(*) FROM ecosystem_event WHERE resolved = 0").fetchone()
        return row[0] if row else 0

    # ----- Cooldown 操作 -----
    def get_cooldown(self, event_key: str) -> Tuple[int, int]:
        """获取冷却状态 (last_day, count)"""
        with self._lock:
            cur = self._conn.cursor()
            row = cur.execute(
                "SELECT last_trigger_world_day, trigger_count FROM event_cooldown WHERE event_key = ?",
                (event_key,)
            ).fetchone()
            if not row:
                return (0, 0)
            return (row[0], row[1])

    def update_cooldown(self, event_key: str, world_day: int):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("""
                INSERT INTO event_cooldown (event_key, last_trigger_world_day, trigger_count)
                VALUES (?, ?, 1)
                ON CONFLICT(event_key) DO UPDATE SET
                    last_trigger_world_day = excluded.last_trigger_world_day,
                    trigger_count = trigger_count + 1
            """, (event_key, world_day))
            self._conn.commit()

    @staticmethod
    def _row_to_event(row) -> EcosystemEvent:
        return EcosystemEvent(
            event_id=row[0], event_key=row[1], name=row[2],
            category=row[3], severity=row[4], region_id=row[5],
            season=row[6], world_day=row[7],
            impacts=json.loads(row[8]) if row[8] else {},
            description=row[9],
            resolved=bool(row[10]),
            timestamp=row[11], resolved_at=row[12] or 0.0,
            effects_applied=json.loads(row[13]) if row[13] else {}
        )


# ============================================================
# 🎲 事件系统核心
# ============================================================

class EventSystem:
    """
    随机事件系统 - 为城邦生态注入生命力和不确定性
    """

    # 同类事件最短间隔天数
    COOLDOWN_DAYS = {
        "flood": 30,
        "drought": 60,
        "plague": 90,
        "earthquake": 180,
        "resource_discovery": 15,
        "immigration_wave": 45,
        "trade_caravan": 20,
        "resource_crisis": 30,
        "social_unrest": 30,
        "trust_collapse": 180,
        "cultural_revival": 60,
        "breakthrough": 45,
    }

    def __init__(self, db: EventsDB, environment_system=None, temporal_system=None):
        self.db = db
        self.environment = environment_system
        self.temporal = temporal_system
        self._interlock_callbacks: List[callable] = []
        # 每个 tick 最多触发事件数
        self.max_events_per_tick = 2
        logger.info("EventSystem initialized")

    def register_interlock(self, callback: callable):
        self._interlock_callbacks.append(callback)

    def set_environment(self, env):
        """注入环境系统（可选）"""
        self.environment = env

    def set_temporal(self, tmp):
        """注入时间系统（可选）"""
        self.temporal = tmp

    # ----- 事件触发 -----
    def tick(self, current_season: str = None, current_entropy: float = 0.0) -> List[EcosystemEvent]:
        """
        事件 tick - 按概率触发随机事件
        """
        if current_season is None and self.temporal:
            current_season = self.temporal.get_season()
        if current_season is None:
            current_season = "spring"

        world_day = 0
        if self.temporal:
            world_day = self.temporal.get_clock()["world_day"]

        regions = self._get_regions()

        triggered: List[EcosystemEvent] = []
        attempts = 0
        max_attempts = self.max_events_per_tick * 3

        while len(triggered) < self.max_events_per_tick and attempts < max_attempts:
            attempts += 1
            event_key = self._select_event(current_season, current_entropy, world_day)
            if not event_key:
                continue
            target_region = random.choice(regions)
            ev = self._trigger_event(event_key, target_region, current_season, world_day)
            if ev:
                triggered.append(ev)

        return triggered

    def _get_regions(self) -> List[str]:
        """获取区域列表，带空列表保护"""
        if self.environment:
            regions = [r.region_id for r in self.environment.list_regions()]
            if regions:
                return regions
        return ["global"]

    def _select_event(self, season: str, entropy: float, world_day: int = 0) -> Optional[str]:
        """
        按概率选择事件 - 关键算法
        概率 = base_probability * season_factor * entropy_factor
        """
        candidates = []
        for key, template in EVENT_TEMPLATES.items():
            # 季节偏好
            season_bias = template.get("season_bias", [])
            if season_bias and season not in season_bias:
                # 不在偏好季节，概率降低
                season_factor = 0.3
            else:
                season_factor = 1.0

            # 熵触发（仅危机事件）
            entropy_trigger = template.get("entropy_trigger", 0.0)
            if entropy_trigger > 0:
                if entropy < entropy_trigger:
                    # 当前熵不够，不触发
                    continue
                entropy_factor = min(2.0, 1.0 + (entropy - entropy_trigger) * 2)
            else:
                # 非熵触发事件，熵高时概率增加
                if entropy > 0.5:
                    entropy_factor = 1.0 + (entropy - 0.5) * 0.5
                else:
                    entropy_factor = 1.0

            # 冷却检查
            last_day, count = self.db.get_cooldown(key)
            cooldown_days = self.COOLDOWN_DAYS.get(key, 30)
            if world_day > 0 and last_day > 0 and (world_day - last_day) < cooldown_days:
                continue  # 仍在冷却期内，跳过

            probability = template["base_probability"] * season_factor * entropy_factor
            candidates.append((key, probability))

        if not candidates:
            return None

        # 加权随机
        total = sum(p for _, p in candidates)
        if total == 0:
            return None
        r = random.random() * total
        cumulative = 0
        for key, p in candidates:
            cumulative += p
            if r < cumulative:
                return key
        return candidates[-1][0]

    def _trigger_event(self, event_key: str, region_id: str,
                       season: str, world_day: int) -> Optional[EcosystemEvent]:
        """实际触发一个事件"""
        template = EVENT_TEMPLATES.get(event_key)
        if not template:
            return None

        # 复制 impacts
        impacts = dict(template["impacts"])

        # 严重度影响
        severity = template["default_severity"]
        sev_mult = {
            EventSeverity.MINOR: 0.5,
            EventSeverity.MODERATE: 1.0,
            EventSeverity.MAJOR: 1.5,
            EventSeverity.CATASTROPHIC: 2.5,
        }.get(severity, 1.0)
        impacts = {k: v * sev_mult for k, v in impacts.items()}

        event_id = f"ev_{uuid.uuid4().hex[:16]}"
        ev = EcosystemEvent(
            event_id=event_id,
            event_key=event_key,
            name=template["name"],
            category=template["category"].value,
            severity=severity.value,
            region_id=region_id,
            season=season,
            world_day=world_day,
            impacts=impacts,
            description=template["description"],
        )

        # 应用效果（如果有环境系统）
        effects_applied = {}
        if self.environment:
            for resource_key, delta in impacts.items():
                # 只对已知资源类型生效
                rt_map = {
                    "energy": "ENERGY",
                    "materials": "MATERIALS",
                    "food": "FOOD",
                    "water": "WATER",
                }
                if resource_key in rt_map:
                    # 从环境系统获取资源配置
                    try:
                        from .environment import ResourceType, RESOURCE_CONFIG
                        resource_type = ResourceType(resource_key)
                        cfg = RESOURCE_CONFIG[resource_type]
                        abs_delta = delta * cfg.get("max_per_region", 100)
                        new_val = self.environment.harvest(
                            region_id, "event_system", resource_type,
                            abs_delta, reason="event:{}".format(event_key)
                        )
                        effects_applied[resource_key] = new_val
                    except Exception as e:
                        logger.warning("Apply event effect failed: {}".format(e))
                elif resource_key == "population":
                    # 人口影响
                    pop_delta = int(delta * POPULATION_IMPACT_MULTIPLIER)
                    success, _ = self.environment.add_population(region_id, pop_delta)
                    effects_applied["population_delta"] = pop_delta

        ev.effects_applied = effects_applied
        ev.resolved = False
        ev.resolved_at = 0
        self.db.insert_event(ev)
        self.db.update_cooldown(event_key, world_day)

        # 互锁通知
        self._notify("event_triggered", {
            "event_id": ev.event_id,
            "event_key": event_key,
            "name": ev.name,
            "category": ev.category,
            "severity": ev.severity,
            "region_id": region_id,
            "impacts": impacts,
            "effects_applied": effects_applied,
        })

        logger.info(f"Event triggered: {ev.name} in {region_id} (severity={ev.severity})")
        return ev

    def list_events(self, region_id: str = None, only_active: bool = False,
                    limit: int = 50) -> List[EcosystemEvent]:
        return self.db.list_events(region_id, only_active, limit)

    def count_active_events(self) -> int:
        return self.db.count_active_events()

    def _notify(self, event_type: str, data: dict):
        for cb in self._interlock_callbacks:
            try:
                cb("events", event_type, data)
            except Exception as e:
                logger.warning(f"Event interlock callback failed: {e}")


# ============================================================
# 🚀 工厂函数
# ============================================================

def create_default_events(data_dir: str = None,
                          environment_system=None,
                          temporal_system=None) -> EventSystem:
    if data_dir is None:
        data_dir = os.environ.get("CITY_STATE_DATA_DIR",
                                   r"C:\Users\dfhai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a45044b9f3d6718577ed1f8\city_state_data\ecosystem")
    db_path = os.path.join(data_dir, "state", "events.db")
    db = EventsDB(db_path)
    sys = EventSystem(db, environment_system, temporal_system)
    return sys


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    # 单独冒烟（不依赖环境系统）
    db = EventsDB("./test_events.db")
    sys = EventSystem(db)
    # 模拟几次 tick
    for i in range(3):
        events = sys.tick(current_season="spring", current_entropy=0.3)
        print(f"\n=== Tick {i+1} ===")
        for ev in events:
            print(f"  [{ev.category}] {ev.name} @ {ev.region_id} ({ev.severity})")
            print(f"    impacts: {ev.impacts}")
    print(f"\n活跃事件数: {sys.count_active_events()}")
    print(f"历史事件总数: {len(sys.list_events(limit=10))}")
    db.close()
    # 清理测试 db
    try:
        os.remove("./test_events.db")
    except OSError:
        pass
    print("冒烟测试通过")
