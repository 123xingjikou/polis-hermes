"""
🌍 城邦生态 - 环境系统 (Environment System)
==========================================

借鉴 GitHub Sugarscape 模型（Epstein & Axtell 经典）的资源-智能体交互范式。
为城邦生态添加"物理世界"基础层，让 Agent 有资源约束和环境压力。

核心能力：
- 资源生成与消耗（4种基础资源：能量/材料/食物/水）
- 资源再生率（参考 Sugarscape 的糖再生机制）
- 环境承载能力（参考 Rat-Utopia 的人口上限）
- 地理区域与资源分布
- 互锁协议接口（与环境、社会、免疫、进化、经济系统联动）

设计原则：
- 不修改 polis_v3.py 核心代码（避免破坏1175代连续运行）
- 独立数据库表（使用独立 .db 文件，避免锁冲突）
- WAL 模式 + 30秒 busy_timeout（与项目其他数据库一致）
- 单连接架构（与项目约定一致）
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
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum

logger = logging.getLogger('polis.environment')


# ============================================================
# 🎯 基础定义
# ============================================================

class ResourceType(Enum):
    """资源类型"""
    ENERGY = "energy"
    MATERIALS = "materials"
    FOOD = "food"
    WATER = "water"


class TerrainType(Enum):
    """地形类型（参考 Sugarscape 的资源分布）"""
    PLAIN = "plain"
    FOREST = "forest"
    HIGHLAND = "highland"
    WATER = "water"
    DESERT = "desert"


class Season(Enum):
    """季节"""
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


# 资源基础配置
RESOURCE_CONFIG = {
    ResourceType.ENERGY: {
        "name": "能量",
        "regeneration_rate": 0.10,
        "max_per_region": 100.0,
        "min_per_region": 0.0,
    },
    ResourceType.MATERIALS: {
        "name": "材料",
        "regeneration_rate": 0.05,
        "max_per_region": 50.0,
        "min_per_region": 0.0,
    },
    ResourceType.FOOD: {
        "name": "食物",
        "regeneration_rate": 0.15,
        "max_per_region": 80.0,
        "min_per_region": 0.0,
    },
    ResourceType.WATER: {
        "name": "水",
        "regeneration_rate": 0.20,
        "max_per_region": 120.0,
        "min_per_region": 0.0,
    },
}

# 季节对资源的影响（参考 Sugarscape 季节周期）
SEASON_EFFECTS = {
    Season.SPRING: {"food": 1.2, "water": 1.1,
                    "energy": 1.0, "materials": 1.0},
    Season.SUMMER: {"food": 1.0, "water": 0.8,
                    "energy": 1.3, "materials": 1.0},
    Season.AUTUMN: {"food": 1.3, "water": 1.0,
                    "energy": 1.0, "materials": 1.2},
    Season.WINTER: {"food": 0.6, "water": 0.9,
                    "energy": 0.7, "materials": 0.8},
}


# ============================================================
# 📦 数据类
# ============================================================

@dataclass
class Region:
    """地理区域（参考 Sugarscape 的网格资源分布）"""
    region_id: str
    name: str
    terrain: str = "plain"
    population: int = 0
    max_population: int = 50  # 环境承载上限
    resources: Dict[str, float] = field(default_factory=dict)  # 当前资源量
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def density_ratio(self) -> float:
        """人口密度比例（0~1）"""
        if self.max_population == 0:
            return 1.0
        return self.population / self.max_population

    def density_effect(self) -> Dict[str, float]:
        """密度效应（参考 Rat-Utopia 的行为沉沦）"""
        d = self.density_ratio()
        if d > 0.9:
            return {"health": -0.3, "productivity": -0.4, "aggression": 0.5}
        elif d > 0.7:
            return {"health": -0.1, "productivity": -0.2, "aggression": 0.2}
        return {}


@dataclass
class ResourceTransaction:
    """资源交易（基础经济行为）"""
    tx_id: str
    region_id: str
    agent_id: str
    resource: str
    amount: float  # 正数=收获，负数=消耗
    balance_after: float
    timestamp: float = field(default_factory=time.time)
    reason: str = ""


# ============================================================
# 🗄️ 数据库层（独立.db，避免锁冲突）
# ============================================================

class EnvironmentDB:
    """环境系统数据库 - 独立连接，WAL模式"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """初始化数据库（单连接复用）"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        self._conn = conn
        self._create_tables()
        logger.info(f"EnvironmentDB initialized: {self.db_path}")

    def _create_tables(self):
        """创建表（用 IF NOT EXISTS 保证幂等）"""
        cur = self._conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS region (
                region_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                terrain TEXT DEFAULT 'plain',
                population INTEGER DEFAULT 0,
                max_population INTEGER DEFAULT 50,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS region_resource (
                region_id TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                amount REAL DEFAULT 0,
                last_regen_ts REAL DEFAULT 0,
                PRIMARY KEY (region_id, resource_type),
                FOREIGN KEY (region_id) REFERENCES region(region_id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resource_tx (
                tx_id TEXT PRIMARY KEY,
                region_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                resource TEXT NOT NULL,
                amount REAL NOT NULL,
                balance_after REAL NOT NULL,
                timestamp REAL NOT NULL,
                reason TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_tx_region_ts
                ON resource_tx(region_id, timestamp DESC)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_tx_agent_ts
                ON resource_tx(agent_id, timestamp DESC)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meta_kv (
                k TEXT PRIMARY KEY,
                v TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def close(self):
        """关闭连接"""
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

    # ----- Region 操作 -----
    def upsert_region(self, region: Region):
        """创建/更新区域（PRAGMA table_info 检查已存在的列）"""
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO region (region_id, name, terrain, population, max_population, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(region_id) DO UPDATE SET
                name=excluded.name,
                terrain=excluded.terrain,
                population=excluded.population,
                max_population=excluded.max_population,
                updated_at=excluded.updated_at
        """, (region.region_id, region.name, region.terrain, region.population,
              region.max_population, region.created_at, region.updated_at))
        self._conn.commit()

    def get_region(self, region_id: str) -> Optional[Region]:
        """获取区域"""
        cur = self._conn.cursor()
        row = cur.execute(
            "SELECT region_id, name, terrain, population, max_population, created_at, updated_at "
            "FROM region WHERE region_id = ?", (region_id,)
        ).fetchone()
        if not row:
            return None
        return Region(
            region_id=row[0], name=row[1], terrain=row[2],
            population=row[3], max_population=row[4],
            created_at=row[5], updated_at=row[6],
        )

    def list_regions(self) -> List[Region]:
        """列出所有区域"""
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT region_id, name, terrain, population, max_population, created_at, updated_at "
            "FROM region ORDER BY region_id"
        ).fetchall()
        return [Region(region_id=r[0], name=r[1], terrain=r[2],
                       population=r[3], max_population=r[4],
                       created_at=r[5], updated_at=r[6]) for r in rows]

    def update_region_population(self, region_id: str, delta: int) -> int:
        """更新区域人口，返回新人口数（合并查询，减少数据库往返）"""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "UPDATE region SET population = MAX(0, MIN(max_population, population + ?)), "
                "updated_at = ? WHERE region_id = ?",
                (delta, time.time(), region_id)
            )
            self._conn.commit()
            row = cur.execute(
                "SELECT population FROM region WHERE region_id = ?", (region_id,)
            ).fetchone()
            return row[0] if row else 0

    # ----- Resource 操作 -----
    def set_resource(self, region_id: str, resource: ResourceType, amount: float):
        """设置资源数量"""
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO region_resource (region_id, resource_type, amount, last_regen_ts)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(region_id, resource_type) DO UPDATE SET
                amount=excluded.amount,
                last_regen_ts=excluded.last_regen_ts
        """, (region_id, resource.value, amount, time.time()))
        self._conn.commit()

    def get_resource(self, region_id: str, resource: ResourceType) -> float:
        """获取资源数量"""
        cur = self._conn.cursor()
        row = cur.execute(
            "SELECT amount FROM region_resource WHERE region_id=? AND resource_type=?",
            (region_id, resource.value)
        ).fetchone()
        return row[0] if row else 0.0

    def get_all_resources(self, region_id: str) -> Dict[str, float]:
        """获取某区域的所有资源"""
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT resource_type, amount FROM region_resource WHERE region_id=?",
            (region_id,)
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def adjust_resource(self, region_id: str, resource: ResourceType, delta: float) -> float:
        """调整资源数量（可正可负），返回调整后的值"""
        with self._lock:
            cur = self._conn.cursor()
            cfg = RESOURCE_CONFIG[resource]
            cur.execute("""
                INSERT INTO region_resource (region_id, resource_type, amount, last_regen_ts)
                VALUES (?, ?, MAX(?, ?), ?)
                ON CONFLICT(region_id, resource_type) DO UPDATE SET
                    amount=MAX(?, MIN(?, region_resource.amount + ?)),
                    last_regen_ts=excluded.last_regen_ts
            """, (
                region_id, resource.value,
                cfg["min_per_region"], delta,
                time.time(),
                cfg["min_per_region"], cfg["max_per_region"], delta
            ))
            self._conn.commit()
            # 在锁内查询，避免竞态
            row = cur.execute(
                "SELECT amount FROM region_resource WHERE region_id=? AND resource_type=?",
                (region_id, resource.value)
            ).fetchone()
            return row[0] if row else 0.0

    def record_transaction(self, tx: ResourceTransaction):
        """记录资源交易"""
        cur = self._conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO resource_tx
                (tx_id, region_id, agent_id, resource, amount, balance_after, timestamp, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (tx.tx_id, tx.region_id, tx.agent_id, tx.resource,
              tx.amount, tx.balance_after, tx.timestamp, tx.reason))
        self._conn.commit()

    def list_transactions(self, region_id: str = None, limit: int = 100) -> List[ResourceTransaction]:
        """列出交易记录"""
        cur = self._conn.cursor()
        if region_id:
            rows = cur.execute(
                "SELECT tx_id, region_id, agent_id, resource, amount, balance_after, timestamp, reason "
                "FROM resource_tx WHERE region_id=? ORDER BY timestamp DESC LIMIT ?",
                (region_id, limit)
            ).fetchall()
        else:
            rows = cur.execute(
                "SELECT tx_id, region_id, agent_id, resource, amount, balance_after, timestamp, reason "
                "FROM resource_tx ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [ResourceTransaction(
            tx_id=r[0], region_id=r[1], agent_id=r[2], resource=r[3],
            amount=r[4], balance_after=r[5], timestamp=r[6], reason=r[7]
        ) for r in rows]

    # ----- Meta KV -----
    def set_meta(self, k: str, v):
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO meta_kv (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (k, json.dumps(v))
        )
        self._conn.commit()

    def get_meta(self, k: str, default=None):
        cur = self._conn.cursor()
        row = cur.execute("SELECT v FROM meta_kv WHERE k=?", (k,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return default


# ============================================================
# 🌍 环境系统核心
# ============================================================

class EnvironmentSystem:
    """
    环境系统 - 借鉴 Sugarscape 的资源-智能体交互范式

    核心职责：
    1. 资源生成与再生
    2. 资源消耗（被 Agent 行为触发）
    3. 环境承载能力检查
    4. 季节性资源波动
    5. 互锁协议通知
    """

    def __init__(self, db: EnvironmentDB):
        self.db = db
        self._season = Season.SPRING
        self._interlock_callbacks: List[callable] = []
        logger.info("EnvironmentSystem initialized")

    def register_interlock(self, callback: callable):
        """注册互锁回调（其他系统订阅环境事件）"""
        self._interlock_callbacks.append(callback)

    def set_season(self, season: Season):
        """设置当前季节"""
        self._season = season
        self.db.set_meta("current_season", season.value)
        logger.info(f"Season changed to: {season.value}")
        self._notify("season_changed", {"season": season.value})

    def get_season(self) -> Season:
        """获取当前季节"""
        saved = self.db.get_meta("current_season", Season.SPRING.value)
        try:
            return Season(saved)
        except ValueError:
            return Season.SPRING

    def get_season_multiplier(self, resource: ResourceType) -> float:
        """获取当前季节对该资源的倍率"""
        season = self.get_season()
        # 资源参数可能是 ResourceType 枚举或字符串
        if hasattr(resource, 'value'):
            resource_key = resource.value
        else:
            resource_key = resource
        return SEASON_EFFECTS.get(season, {}).get(resource_key, 1.0)

    # ----- Region 管理 -----
    def create_region(self, region_id: str, name: str,
                      terrain: str = "plain", max_population: int = 50) -> Region:
        """创建区域"""
        region = Region(
            region_id=region_id, name=name, terrain=terrain,
            max_population=max_population
        )
        self.db.upsert_region(region)
        # 初始化资源（按地形分配）
        for resource_type, cfg in RESOURCE_CONFIG.items():
            initial = cfg["max_per_region"] * random.uniform(0.5, 1.0)
            self.db.set_resource(region_id, resource_type, initial)
        logger.info(f"Region created: {region_id} ({terrain})")
        self._notify("region_created", {"region_id": region_id, "name": name, "terrain": terrain})
        return region

    def list_regions(self) -> List[Region]:
        """列出所有区域"""
        return self.db.list_regions()

    def get_region(self, region_id: str) -> Optional[Region]:
        return self.db.get_region(region_id)

    # ----- 资源操作 -----
    def consume(self, region_id: str, agent_id: str,
                resource: ResourceType, amount: float, reason: str = "") -> Tuple[bool, float]:
        """
        消耗资源（Agent 行为触发）
        返回 (是否成功, 剩余量)

        使用原子操作避免竞态条件：
        1. 在锁内执行检查和扣减
        2. 使用 SQL 条件确保只有资源足够时才扣减
        """
        with self.db._lock:
            cur = self.db._conn.cursor()
            # 先检查当前值
            row = cur.execute(
                "SELECT amount FROM region_resource WHERE region_id=? AND resource_type=?",
                (region_id, resource.value)
            ).fetchone()
            current = row[0] if row else 0.0

            if current < amount:
                logger.debug(f"Insufficient {resource.value} in {region_id}: need {amount}, have {current}")
                self._notify("resource_shortage", {
                    "region_id": region_id, "resource": resource.value,
                    "needed": amount, "available": current
                })
                return False, current

            # 原子扣减（在锁内）
            cfg = RESOURCE_CONFIG[resource]
            cur.execute("""
                UPDATE region_resource SET
                    amount=MAX(?, amount - ?),
                    last_regen_ts=?
                WHERE region_id=? AND resource_type=? AND amount >= ?
            """, (
                cfg["min_per_region"], amount, time.time(),
                region_id, resource.value, amount
            ))
            self.db._conn.commit()

            # 获取新余额
            row = cur.execute(
                "SELECT amount FROM region_resource WHERE region_id=? AND resource_type=?",
                (region_id, resource.value)
            ).fetchone()
            new_balance = row[0] if row else 0.0

        # 记录交易
        tx = ResourceTransaction(
            tx_id=f"tx_{int(time.time()*1000)}_{random.randint(1000, 9999)}",
            region_id=region_id, agent_id=agent_id,
            resource=resource.value, amount=-amount,
            balance_after=new_balance, reason=reason
        )
        self.db.record_transaction(tx)
        return True, new_balance

    def harvest(self, region_id: str, agent_id: str,
                resource: ResourceType, amount: float, reason: str = "") -> float:
        """
        收获/补充资源
        返回新的资源量

        使用锁保护，避免并发冲突
        """
        new_balance = self.db.adjust_resource(region_id, resource, amount)
        tx = ResourceTransaction(
            tx_id=f"tx_{int(time.time()*1000)}_{random.randint(1000, 9999)}",
            region_id=region_id, agent_id=agent_id,
            resource=resource.value, amount=amount,
            balance_after=new_balance, reason=reason
        )
        self.db.record_transaction(tx)
        return new_balance

    def get_resource(self, region_id: str, resource: ResourceType) -> float:
        return self.db.get_resource(region_id, resource)

    def get_all_resources(self, region_id: str) -> Dict[str, float]:
        return self.db.get_all_resources(region_id)

    # ----- 资源再生（参考 Sugarscape） -----
    def regenerate(self, region_id: str, dt_seconds: float = 1.0):
        """
        资源再生 - 关键 tick 循环
        公式：new_amount = min(max, current + rate * max * season_mult * dt)
        
        改进：使用原子 UPDATE 替代 read-modify-write，消除竞态条件
        """
        season = self.get_season()
        for resource_type, cfg in RESOURCE_CONFIG.items():
            season_mult = SEASON_EFFECTS.get(season, {}).get(resource_type.value, 1.0)
            # 再生量
            regen = cfg["regeneration_rate"] * cfg["max_per_region"] * season_mult * dt_seconds
            max_amount = cfg["max_per_region"]
            # 原子操作：在 SQL 中完成 read-modify-write，避免竞态
            with self.db._lock:
                self.db._conn.execute(
                    "UPDATE region_resource SET amount = MIN(?, amount + ?), "
                    "updated_at = ? WHERE region_id = ? AND resource_type = ?",
                    (max_amount, regen, time.time(), region_id, resource_type.value)
                )
                self.db._conn.commit()
        # 资源再生会降低环境熵
        self._notify("resources_regenerated", {"region_id": region_id, "season": season.value})

    def regenerate_all(self, dt_seconds: float = 1.0):
        """所有区域资源再生"""
        for region in self.list_regions():
            self.regenerate(region.region_id, dt_seconds)

    # ----- 人口管理 -----
    def add_population(self, region_id: str, delta: int) -> Tuple[bool, int]:
        """
        增加人口（Agent 迁移或出生触发）
        返回 (是否成功, 新人口数)
        """
        region = self.get_region(region_id)
        if not region:
            return False, 0
        if region.population + delta > region.max_population:
            logger.debug(f"Region {region_id} at capacity: {region.population}/{region.max_population}")
            self._notify("region_at_capacity", {
                "region_id": region_id,
                "current": region.population,
                "max": region.max_population
            })
            return False, region.population
        new_pop = self.db.update_region_population(region_id, delta)
        return True, new_pop

    def get_density_effect(self, region_id: str) -> Dict[str, float]:
        """获取区域密度效应"""
        region = self.get_region(region_id)
        if not region:
            return {}
        return region.density_effect()

    # ----- 生态熵指标 -----
    def calculate_entropy(self) -> float:
        """
        生态熵：衡量系统混乱度
        = 加权(资源稀缺度 + 人口密度压力 + 区域不均衡)
        范围：0（完美有序）~ 1（极度混乱）
        """
        regions = self.list_regions()
        if not regions:
            return 0.0

        total_entropy = 0.0
        for region in regions:
            # 资源稀缺度（资源越少，熵越高）
            resources = self.get_all_resources(region.region_id)
            scarcity = 0.0
            for resource_type, cfg in RESOURCE_CONFIG.items():
                current = resources.get(resource_type.value, 0)
                scarcity += 1.0 - (current / cfg["max_per_region"])
            scarcity /= len(RESOURCE_CONFIG)

            # 人口密度压力
            density = region.density_ratio()

            # 综合
            total_entropy += (0.6 * scarcity + 0.4 * density)

        return min(1.0, total_entropy / len(regions))

    # ----- 内部通知 -----
    def _notify(self, event_type: str, data: dict):
        """通知互锁系统"""
        for cb in self._interlock_callbacks:
            try:
                cb("environment", event_type, data)
            except Exception as e:
                logger.warning(f"Interlock callback failed: {e}")


# ============================================================
# 🚀 工厂函数
# ============================================================

def create_default_environment(data_dir: str = None) -> EnvironmentSystem:
    """创建带默认配置的环境系统"""
    if data_dir is None:
        data_dir = os.environ.get("CITY_STATE_DATA_DIR",
                                   r"C:\Users\dfhai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a45044b9f3d6718577ed1f8\city_state_data\ecosystem")
    db_path = os.path.join(data_dir, "state", "environment.db")
    db = EnvironmentDB(db_path)
    env = EnvironmentSystem(db)

    # 如果没有任何区域，创建默认三个区域（参考 Sugarscape 的双糖山分布）
    if not env.list_regions():
        env.create_region("central_plains", "中央平原", "plain", max_population=80)
        env.create_region("eastern_forest", "东部森林", "forest", max_population=50)
        env.create_region("northern_hills", "北部山丘", "highland", max_population=30)
        logger.info("Default regions initialized")

    return env


if __name__ == "__main__":
    # 简单冒烟测试
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    env = create_default_environment()
    print(f"环境系统创建成功，区域数：{len(env.list_regions())}")
    for r in env.list_regions():
        print(f"  区域: {r.name} ({r.terrain}) 人口 {r.population}/{r.max_population}")
        res = env.get_all_resources(r.region_id)
        for k, v in res.items():
            print(f"    {k}: {v:.1f}")
    print(f"生态熵: {env.calculate_entropy():.3f}")
    # 测试消耗
    success, remaining = env.consume("central_plains", "agent_001",
                                      ResourceType.FOOD, 5.0, "test_consume")
    print(f"消耗测试: 成功={success}, 剩余={remaining:.1f}")
    # 测试再生
    env.regenerate_all(10.0)
    print(f"再生后生态熵: {env.calculate_entropy():.3f}")
    env.db.close()
    print("冒烟测试通过")
