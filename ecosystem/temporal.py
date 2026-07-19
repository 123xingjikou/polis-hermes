"""
⏰ 城邦生态 - 时间系统 (Temporal System)
==========================================

借鉴 Sugarscape 的季节周期和昼夜循环概念。
为城邦生态添加时间维度，让生态行为有节奏和周期。

核心能力：
- 昼夜循环（影响 Agent 活动模式）
- 季节系统（资源波动、疾病爆发周期）
- 日历系统（事件纪念日、历史节点）
- 时间加速/减速控制（调试和观察）
- 与环境系统的深度联动

设计原则：
- 独立数据库（time_calendar.db）
- 复用环境系统的季节信息
- 互锁协议通知其他系统
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
import json
import math
import logging
import os
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


logger = logging.getLogger('polis.temporal')


# ============================================================
# 🎯 基础定义
# ============================================================

class TimeOfDay(Enum):
    """一天中的时段"""
    DAWN = "dawn"           # 黎明 5:00-7:00
    MORNING = "morning"     # 早晨 7:00-12:00
    NOON = "noon"           # 中午 12:00-14:00
    AFTERNOON = "afternoon" # 下午 14:00-18:00
    DUSK = "dusk"           # 黄昏 18:00-20:00
    NIGHT = "night"         # 夜晚 20:00-5:00


class Era(Enum):
    """时代/纪元"""
    DAWN = "dawn"           # 创世期
    GROWTH = "growth"       # 成长期
    PROSPERITY = "prosperity"  # 繁荣期
    CRISIS = "crisis"       # 危机期
    DECLINE = "decline"     # 衰退期
    REBIRTH = "rebirth"     # 重生期


# 时段对 Agent 活动的影响
TIME_OF_DAY_EFFECTS = {
    TimeOfDay.DAWN: {"activity": 0.6, "discovery": 1.2, "social": 0.5},
    TimeOfDay.MORNING: {"activity": 1.3, "discovery": 1.0, "social": 0.9},
    TimeOfDay.NOON: {"activity": 1.0, "discovery": 0.8, "social": 1.2},
    TimeOfDay.AFTERNOON: {"activity": 1.2, "discovery": 1.1, "social": 1.0},
    TimeOfDay.DUSK: {"activity": 0.7, "discovery": 1.0, "social": 1.3},
    TimeOfDay.NIGHT: {"activity": 0.3, "discovery": 0.5, "social": 0.7},
}


# ============================================================
# 📦 数据类
# ============================================================

@dataclass
class CalendarEntry:
    """日历条目（重要事件、纪念日）"""
    entry_id: str
    title: str
    entry_type: str  # festival/commemoration/historical
    day_of_year: int  # 1-365
    description: str = ""
    created_at: float = field(default_factory=time.time)


# ============================================================
# 🗄️ 数据库层
# ============================================================

class TemporalDB:
    """时间系统数据库 - 独立.db，WAL模式"""

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
        logger.info(f"TemporalDB initialized: {self.db_path}")

    def _create_tables(self):
        cur = self._conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clock (
                clock_id INTEGER PRIMARY KEY CHECK (clock_id = 1),
                world_day INTEGER NOT NULL DEFAULT 1,
                world_year INTEGER NOT NULL DEFAULT 1,
                day_of_year INTEGER NOT NULL DEFAULT 1,
                hour INTEGER NOT NULL DEFAULT 6,
                minute INTEGER NOT NULL DEFAULT 0,
                tick_count INTEGER NOT NULL DEFAULT 0,
                time_scale REAL NOT NULL DEFAULT 1.0,
                last_real_ts REAL NOT NULL
            )
        """)
        # 确保单行时钟存在
        cur.execute("""
            INSERT OR IGNORE INTO clock
                (clock_id, world_day, world_year, day_of_year, hour, minute,
                 tick_count, time_scale, last_real_ts)
            VALUES (1, 1, 1, 1, 6, 0, 0, 1.0, ?)
        """, (time.time(),))
        cur.execute("""
            CREATE TABLE IF NOT EXISTS calendar_entry (
                entry_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                day_of_year INTEGER NOT NULL,
                description TEXT DEFAULT '',
                created_at REAL NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS time_event (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                ts REAL NOT NULL,
                world_day INTEGER NOT NULL,
                data TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_day
                ON time_event(world_day, event_type)
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

    # ----- Clock 操作 -----
    def get_clock(self) -> dict:
        cur = self._conn.cursor()
        row = cur.execute("""
            SELECT world_day, world_year, day_of_year, hour, minute,
                   tick_count, time_scale, last_real_ts
            FROM clock WHERE clock_id = 1
        """).fetchone()
        return {
            "world_day": row[0], "world_year": row[1], "day_of_year": row[2],
            "hour": row[3], "minute": row[4],
            "tick_count": row[5], "time_scale": row[6],
            "last_real_ts": row[7]
        }

    def update_clock(self, **kwargs):
        """部分更新时钟字段"""
        allowed = {"world_day", "world_year", "day_of_year", "hour",
                   "minute", "tick_count", "time_scale", "last_real_ts"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [time.time()]
        cur = self._conn.cursor()
        cur.execute(f"UPDATE clock SET {sets}, last_real_ts=? WHERE clock_id=1", vals)
        self._conn.commit()

    # ----- Calendar 操作 -----
    def add_calendar_entry(self, entry: CalendarEntry):
        cur = self._conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO calendar_entry
                (entry_id, title, entry_type, day_of_year, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (entry.entry_id, entry.title, entry.entry_type,
              entry.day_of_year, entry.description, entry.created_at))
        self._conn.commit()

    def list_calendar_entries(self, day_of_year: int = None) -> List[CalendarEntry]:
        cur = self._conn.cursor()
        if day_of_year is not None:
            rows = cur.execute(
                "SELECT entry_id, title, entry_type, day_of_year, description, created_at "
                "FROM calendar_entry WHERE day_of_year = ? ORDER BY entry_id",
                (day_of_year,)
            ).fetchall()
        else:
            rows = cur.execute(
                "SELECT entry_id, title, entry_type, day_of_year, description, created_at "
                "FROM calendar_entry ORDER BY day_of_year, entry_id"
            ).fetchall()
        return [CalendarEntry(
            entry_id=r[0], title=r[1], entry_type=r[2],
            day_of_year=r[3], description=r[4], created_at=r[5]
        ) for r in rows]

    # ----- Event log -----
    def log_event(self, event_type: str, world_day: int, data: dict = None):
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO time_event (event_type, ts, world_day, data)
            VALUES (?, ?, ?, ?)
        """, (event_type, time.time(), world_day, json.dumps(data or {})))
        self._conn.commit()

    def count_events(self, event_type: str = None) -> int:
        cur = self._conn.cursor()
        if event_type:
            row = cur.execute(
                "SELECT COUNT(*) FROM time_event WHERE event_type = ?", (event_type,)
            ).fetchone()
        else:
            row = cur.execute("SELECT COUNT(*) FROM time_event").fetchone()
        return row[0] if row else 0


# ============================================================
# ⏰ 时间系统核心
# ============================================================

class TemporalSystem:
    """
    时间系统 - 昼夜循环 + 季节 + 时代
    借鉴 Sugarscape 的周期模型
    """

    # 一天的小时数
    HOURS_PER_DAY = 24
    DAYS_PER_YEAR = 360
    # 季节分布
    SEASON_DURATION = DAYS_PER_YEAR // 4  # 90 天
    # 时段边界
    TIME_OF_DAY_BOUNDARIES = {
        TimeOfDay.DAWN: (5, 7),
        TimeOfDay.MORNING: (7, 12),
        TimeOfDay.NOON: (12, 14),
        TimeOfDay.AFTERNOON: (14, 18),
        TimeOfDay.DUSK: (18, 20),
        TimeOfDay.NIGHT: (20, 24),
    }

    def __init__(self, db: TemporalDB):
        self.db = db
        self._interlock_callbacks: List[callable] = []
        logger.info("TemporalSystem initialized")

    def register_interlock(self, callback: callable):
        self._interlock_callbacks.append(callback)

    # ----- 时钟推进 -----
    def advance(self, hours: float = 1.0):
        """
        推进时间（按小时）
        自动跨日、跨年
        """
        if hours < 0:
            raise ValueError(f"hours must be non-negative, got {hours}")
        clock = self.db.get_clock()
        new_minute = clock["minute"] + (hours - int(hours)) * 60
        hour_increment = int(hours) + int(new_minute // 60)
        new_minute = new_minute % 60

        new_hour = clock["hour"] + hour_increment
        day_increment = 0
        while new_hour >= self.HOURS_PER_DAY:
            new_hour -= self.HOURS_PER_DAY
            day_increment += 1

        new_day_of_year = clock["day_of_year"] + day_increment
        new_world_day = clock["world_day"] + day_increment

        year_increment = 0
        while new_day_of_year > self.DAYS_PER_YEAR:
            new_day_of_year -= self.DAYS_PER_YEAR
            year_increment += 1
        new_world_year = clock["world_year"] + year_increment

        self.db.update_clock(
            world_day=new_world_day,
            world_year=new_world_year,
            day_of_year=new_day_of_year,
            hour=int(new_hour),
            minute=int(new_minute),
            tick_count=clock["tick_count"] + 1
        )

        # 检查跨日
        if day_increment > 0:
            self._on_new_day(new_world_day, new_day_of_year)
        if year_increment > 0:
            self._on_new_year(new_world_year)

    def set_time_scale(self, scale: float):
        """设置时间加速倍率"""
        assert scale > 0, "time_scale must be > 0"
        self.db.update_clock(time_scale=scale)
        logger.info(f"Time scale set to: {scale}x")

    def get_time_scale(self) -> float:
        return self.db.get_clock()["time_scale"]

    def get_clock(self) -> dict:
        return self.db.get_clock()

    # ----- 时段 -----
    def get_time_of_day(self) -> TimeOfDay:
        """根据当前小时返回时段"""
        clock = self.db.get_clock()
        h = clock["hour"]
        if 5 <= h < 7:
            return TimeOfDay.DAWN
        elif 7 <= h < 12:
            return TimeOfDay.MORNING
        elif 12 <= h < 14:
            return TimeOfDay.NOON
        elif 14 <= h < 18:
            return TimeOfDay.AFTERNOON
        elif 18 <= h < 20:
            return TimeOfDay.DUSK
        else:
            return TimeOfDay.NIGHT

    def get_time_of_day_effects(self) -> Dict[str, float]:
        """获取当前时段对 Agent 活动的影响"""
        return TIME_OF_DAY_EFFECTS.get(self.get_time_of_day(), {})

    # ----- 季节（依赖环境系统的定义） -----
    def get_season(self) -> str:
        """返回当前季节字符串"""
        clock = self.db.get_clock()
        doy = clock["day_of_year"]
        if doy <= self.SEASON_DURATION:
            return "spring"
        elif doy <= self.SEASON_DURATION * 2:
            return "summer"
        elif doy <= self.SEASON_DURATION * 3:
            return "autumn"
        else:
            return "winter"

    # ----- 时代 -----
    def get_era(self) -> Era:
        """根据世界年份判断时代"""
        clock = self.db.get_clock()
        year = clock["world_year"]
        # 简单规则：前10年成长期，之后看生态状态
        if year < 3:
            return Era.DAWN
        elif year < 10:
            return Era.GROWTH
        else:
            return Era.PROSPERITY

    # ----- 日历 -----
    def add_calendar_entry(self, entry_id: str, title: str,
                           entry_type: str, day_of_year: int,
                           description: str = ""):
        """添加日历条目"""
        entry = CalendarEntry(
            entry_id=entry_id, title=title, entry_type=entry_type,
            day_of_year=day_of_year, description=description
        )
        self.db.add_calendar_entry(entry)
        logger.info(f"Calendar entry added: {title} (day {day_of_year})")

    def get_today_events(self) -> List[CalendarEntry]:
        """获取今日日历事件"""
        return self.db.list_calendar_entries(self.db.get_clock()["day_of_year"])

    def list_calendar(self) -> List[CalendarEntry]:
        return self.db.list_calendar_entries()

    # ----- 内部事件 -----
    def _on_new_day(self, world_day: int, day_of_year: int):
        """新一天触发"""
        season = self.get_season()
        self.db.log_event("new_day", world_day, {"day_of_year": day_of_year, "season": season})
        self._notify("new_day", {"world_day": world_day, "day_of_year": day_of_year, "season": season})

    def _on_new_year(self, world_year: int):
        """新年触发"""
        self.db.log_event("new_year", world_year, {"year": world_year})
        self._notify("new_year", {"year": world_year})

    def _notify(self, event_type: str, data: dict):
        for cb in self._interlock_callbacks:
            try:
                cb("temporal", event_type, data)
            except Exception as e:
                logger.warning(f"Temporal interlock callback failed: {e}")


# ============================================================
# 🚀 工厂函数
# ============================================================

def create_default_temporal(data_dir: str = None) -> TemporalSystem:
    if data_dir is None:
        data_dir = os.environ.get("CITY_STATE_DATA_DIR",
                                   r"C:\Users\dfhai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a45044b9f3d6718577ed1f8\city_state_data\ecosystem")
    db_path = os.path.join(data_dir, "state", "temporal.db")
    db = TemporalDB(db_path)
    sys = TemporalSystem(db)

    # 添加默认节日
    if not sys.list_calendar():
        sys.add_calendar_entry("new_year", "新年", "festival", 1, "新年庆典")
        sys.add_calendar_entry("spring_fest", "春之祭", "festival", 30, "春季庆祝")
        sys.add_calendar_entry("harvest", "丰收节", "festival", 270, "秋收庆典")
        sys.add_calendar_entry("winter_solstice", "冬至", "festival", 355, "冬至纪念")
        logger.info("Default calendar initialized")

    return sys


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    ts = create_default_temporal()
    print(f"时间系统创建成功")
    print(f"当前时钟: {ts.get_clock()}")
    print(f"当前时段: {ts.get_time_of_day().value}")
    print(f"当前季节: {ts.get_season()}")
    print(f"当前时代: {ts.get_era().value}")
    print(f"时段效果: {ts.get_time_of_day_effects()}")
    print(f"今日事件: {[e.title for e in ts.get_today_events()]}")

    # 推进时间
    ts.advance(168)  # 一周
    print(f"推进一周后: day={ts.get_clock()['world_day']}, hour={ts.get_clock()['hour']}")
    ts.db.close()
    print("冒烟测试通过")
