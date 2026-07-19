"""
🧠 城邦生态 - 复杂度分层系统 (Complexity System)
===============================================

定义Agent从简单到超级智能体的成长阶梯：
- L0 刺激-反应 → L1 经验学习 → L2 多步规划 → L3 元认知 → L4 创造性 → L5 超级智能
- 技能树系统（前置条件 + 熟练度 + 组合创新）
- 文明级知识积累（全Agent共享的技术库）
- 元学习能力（学习如何学习）

设计原则：
- 独立数据库（complexity.db）
- 与 evolution.py 协同：认知基因为基础，复杂度为表现
- 互锁协议集成
"""

import sys as _ecosystem_sys
import importlib as _ecosystem_importlib
if 'inspect' in _ecosystem_sys.modules and not hasattr(_ecosystem_sys.modules.get('inspect'), 'get_annotations'):
    del _ecosystem_sys.modules['inspect']
    import inspect
else:
    import inspect

import sqlite3
import time
import random
import json
import logging
import os
import hashlib
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum

logger = logging.getLogger('polis.complexity')


# ============================================================
# 🎯 常量定义
# ============================================================

MASTERY_THRESHOLD = 50  # 技能精通等级阈值


# ============================================================
# 🎯 基础定义
# ============================================================

class SkillType(Enum):
    """技能类型"""
    GATHERING = "gathering"          # 采集
    CRAFTING = "crafting"            # 制造
    TRADING = "trading"              # 交易
    SCOUTING = "scouting"            # 探索
    DIPLOMACY = "diplomacy"          # 外交
    LEADERSHIP = "leadership"        # 领导
    INNOVATION = "innovation"        # 创新
    TEACHING = "teaching"            # 教学
    HEALING = "healing"              # 治疗
    DEFENSE = "defense"              # 防御
    ANALYSIS = "analysis"            # 分析
    PLANNING = "planning"            # 规划
    META_LEARNING = "meta_learning"  # 元学习
    ABSTRACT_REASONING = "abstract_reasoning"  # 抽象推理
    CREATIVITY = "creativity"        # 创造力


# 技能树定义：技能 → 前置技能列表
SKILL_PREREQUISITES: Dict[SkillType, List[SkillType]] = {
    SkillType.GATHERING: [],
    SkillType.SCOUTING: [],
    SkillType.HEALING: [],
    SkillType.DEFENSE: [],
    SkillType.TRADING: [SkillType.GATHERING],
    SkillType.CRAFTING: [SkillType.GATHERING],
    SkillType.DIPLOMACY: [SkillType.TRADING, SkillType.SCOUTING],
    SkillType.LEADERSHIP: [SkillType.DIPLOMACY],
    SkillType.INNOVATION: [SkillType.CRAFTING, SkillType.SCOUTING],
    SkillType.TEACHING: [SkillType.LEADERSHIP],
    SkillType.ANALYSIS: [SkillType.GATHERING, SkillType.SCOUTING],
    SkillType.PLANNING: [SkillType.ANALYSIS, SkillType.LEADERSHIP],
    SkillType.META_LEARNING: [SkillType.ANALYSIS, SkillType.INNOVATION],
    SkillType.ABSTRACT_REASONING: [SkillType.ANALYSIS, SkillType.PLANNING],
    SkillType.CREATIVITY: [SkillType.INNOVATION, SkillType.ABSTRACT_REASONING, SkillType.META_LEARNING],
}

# 技能→复杂度贡献值
SKILL_COMPLEXITY_VALUE: Dict[SkillType, int] = {
    SkillType.GATHERING: 1,
    SkillType.SCOUTING: 1,
    SkillType.HEALING: 2,
    SkillType.DEFENSE: 2,
    SkillType.TRADING: 3,
    SkillType.CRAFTING: 4,
    SkillType.DIPLOMACY: 5,
    SkillType.LEADERSHIP: 6,
    SkillType.INNOVATION: 8,
    SkillType.TEACHING: 7,
    SkillType.ANALYSIS: 8,
    SkillType.PLANNING: 10,
    SkillType.META_LEARNING: 15,
    SkillType.ABSTRACT_REASONING: 15,
    SkillType.CREATIVITY: 20,
}

# 文明级里程碑（全种群共享）
CIVILIZATION_MILESTONES = {
    "fire_mastery": {"name": "掌握火种", "required_skills": [SkillType.GATHERING], "bonus": 1.1},
    "tool_making": {"name": "工具制造", "required_skills": [SkillType.CRAFTING], "bonus": 1.1},
    "trade_network": {"name": "贸易网络", "required_skills": [SkillType.TRADING], "bonus": 1.15},
    "language": {"name": "语言系统", "required_skills": [SkillType.DIPLOMACY], "bonus": 1.2},
    "governance": {"name": "治理体系", "required_skills": [SkillType.LEADERSHIP], "bonus": 1.2},
    "writing": {"name": "书写系统", "required_skills": [SkillType.TEACHING], "bonus": 1.25},
    "philosophy": {"name": "哲学思想", "required_skills": [SkillType.ANALYSIS], "bonus": 1.3},
    "science": {"name": "科学方法", "required_skills": [SkillType.META_LEARNING], "bonus": 1.4},
    "super_intelligence": {"name": "超级智能", "required_skills": [SkillType.CREATIVITY], "bonus": 1.5},
}


@dataclass
class SkillMastery:
    """技能熟练度"""
    skill_type: SkillType
    level: float = 0.0           # 0-100
    experience: float = 0.0
    practiced_count: int = 0
    last_practiced: float = 0.0
    unlocked: bool = False

    def gain_experience(self, amount: float):
        """获得经验"""
        self.experience += amount
        self.practiced_count += 1
        self.last_practiced = time.time()
        # 经验曲线：升级越来越难
        new_level = min(100, (self.experience / 10) ** 0.7 * 10)
        leveled_up = new_level > self.level
        self.level = new_level
        if self.level >= 10.0 and not self.unlocked:
            self.unlocked = True
        return leveled_up

    def to_dict(self) -> Dict:
        return {
            'skill_type': self.skill_type.value,
            'level': round(self.level, 2),
            'experience': round(self.experience, 2),
            'practiced_count': self.practiced_count,
            'unlocked': self.unlocked,
        }


@dataclass
class ComplexityProfile:
    """复杂度画像 - Agent在超级智能道路上的位置"""
    agent_id: str
    complexity_level: int = 0          # 0-5
    total_skill_value: int = 0
    skills_mastered: int = 0
    meta_learning_factor: float = 1.0  # 元学习加速因子
    innovation_count: int = 0
    knowledge_transfer_count: int = 0
    generation: int = 0
    cognitive_traits: Dict = field(default_factory=dict)

    def update_complexity(self) -> int:
        """计算复杂度等级"""
        value = self.total_skill_value
        if value >= 80:
            self.complexity_level = 5  # L5 超级智能
        elif value >= 60:
            self.complexity_level = 4  # L4 创造性
        elif value >= 40:
            self.complexity_level = 3  # L3 元认知
        elif value >= 25:
            self.complexity_level = 2  # L2 规划
        elif value >= 10:
            self.complexity_level = 1  # L1 经验学习
        else:
            self.complexity_level = 0  # L0 刺激-反应
        return self.complexity_level

    def to_dict(self) -> Dict:
        return {
            'agent_id': self.agent_id,
            'complexity_level': self.complexity_level,
            'total_skill_value': self.total_skill_value,
            'skills_mastered': self.skills_mastered,
            'meta_learning_factor': round(self.meta_learning_factor, 3),
            'innovation_count': self.innovation_count,
            'knowledge_transfer_count': self.knowledge_transfer_count,
            'generation': self.generation,
        }


# ============================================================
# 🗄️ 数据库层
# ============================================================

class ComplexityDB:
    """复杂度系统数据库"""

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
        logger.info(f"ComplexityDB initialized: {self.db_path}")

    def _create_tables(self):
        cur = self._conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS complexity_profile (
                agent_id TEXT PRIMARY KEY,
                complexity_level INTEGER NOT NULL,
                total_skill_value INTEGER NOT NULL,
                skills_mastered INTEGER NOT NULL,
                meta_learning_factor REAL NOT NULL,
                innovation_count INTEGER NOT NULL,
                knowledge_transfer_count INTEGER NOT NULL,
                generation INTEGER NOT NULL,
                cognitive_traits TEXT DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS skill_mastery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                skill_type TEXT NOT NULL,
                level REAL NOT NULL,
                experience REAL NOT NULL,
                practiced_count INTEGER NOT NULL,
                unlocked INTEGER NOT NULL,
                last_practiced REAL NOT NULL,
                UNIQUE(agent_id, skill_type)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS civilization_milestone (
                milestone_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                achieved_by TEXT,
                generation INTEGER NOT NULL,
                achieved_at REAL NOT NULL,
                global_bonus REAL NOT NULL DEFAULT 1.0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS innovation_record (
                innovation_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                innovation_type TEXT NOT NULL,
                description TEXT NOT NULL,
                generation INTEGER NOT NULL,
                complexity_level INTEGER NOT NULL,
                impact_score REAL NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_skill_agent
                ON skill_mastery(agent_id, skill_type)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_profile_complexity
                ON complexity_profile(complexity_level DESC)
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

    def upsert_profile(self, profile: ComplexityProfile):
        cur = self._conn.cursor()
        now = time.time()
        cur.execute("""
            INSERT OR REPLACE INTO complexity_profile
                (agent_id, complexity_level, total_skill_value, skills_mastered,
                 meta_learning_factor, innovation_count, knowledge_transfer_count,
                 generation, cognitive_traits, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile.agent_id, profile.complexity_level, profile.total_skill_value,
            profile.skills_mastered, profile.meta_learning_factor,
            profile.innovation_count, profile.knowledge_transfer_count,
            profile.generation, json.dumps(profile.cognitive_traits),
            now, now,
        ))
        self._conn.commit()

    def get_profile(self, agent_id: str) -> Optional[ComplexityProfile]:
        cur = self._conn.cursor()
        row = cur.execute(
            "SELECT agent_id, complexity_level, total_skill_value, skills_mastered, "
            "meta_learning_factor, innovation_count, knowledge_transfer_count, "
            "generation, cognitive_traits "
            "FROM complexity_profile WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        if not row:
            return None
        traits = {}
        try:
            traits = json.loads(row[8]) if row[8] else {}
        except json.JSONDecodeError:
            pass
        return ComplexityProfile(
            agent_id=row[0], complexity_level=row[1], total_skill_value=row[2],
            skills_mastered=row[3], meta_learning_factor=row[4],
            innovation_count=row[5], knowledge_transfer_count=row[6],
            generation=row[7], cognitive_traits=traits,
        )

    def list_profiles(self, limit: int = 50, order_by: str = "complexity_level DESC") -> List[ComplexityProfile]:
        cur = self._conn.cursor()
        allowed = {"complexity_level DESC", "total_skill_value DESC", "generation DESC"}
        if order_by not in allowed:
            order_by = "complexity_level DESC"
        rows = cur.execute(
            f"SELECT agent_id, complexity_level, total_skill_value, skills_mastered, "
            f"meta_learning_factor, innovation_count, knowledge_transfer_count, "
            f"generation, cognitive_traits FROM complexity_profile ORDER BY {order_by} LIMIT ?",
            (limit,)
        ).fetchall()
        profiles = []
        for row in rows:
            traits = {}
            try:
                traits = json.loads(row[8]) if row[8] else {}
            except json.JSONDecodeError:
                pass
            profiles.append(ComplexityProfile(
                agent_id=row[0], complexity_level=row[1], total_skill_value=row[2],
                skills_mastered=row[3], meta_learning_factor=row[4],
                innovation_count=row[5], knowledge_transfer_count=row[6],
                generation=row[7], cognitive_traits=traits,
            ))
        return profiles

    def upsert_skill(self, agent_id: str, skill: SkillMastery):
        cur = self._conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO skill_mastery
                (agent_id, skill_type, level, experience, practiced_count, unlocked, last_practiced)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (agent_id, skill.skill_type.value, skill.level, skill.experience,
              skill.practiced_count, 1 if skill.unlocked else 0, skill.last_practiced))
        self._conn.commit()

    def get_skill(self, agent_id: str, skill_type: SkillType) -> Optional[SkillMastery]:
        cur = self._conn.cursor()
        row = cur.execute(
            "SELECT skill_type, level, experience, practiced_count, unlocked, last_practiced "
            "FROM skill_mastery WHERE agent_id = ? AND skill_type = ?",
            (agent_id, skill_type.value)
        ).fetchone()
        if not row:
            return None
        return SkillMastery(
            skill_type=SkillType(row[0]),
            level=row[1],
            experience=row[2],
            practiced_count=row[3],
            unlocked=bool(row[4]),
            last_practiced=row[5],
        )

    def list_agent_skills(self, agent_id: str) -> List[SkillMastery]:
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT skill_type, level, experience, practiced_count, unlocked, last_practiced "
            "FROM skill_mastery WHERE agent_id = ? ORDER BY level DESC",
            (agent_id,)
        ).fetchall()
        return [
            SkillMastery(
                skill_type=SkillType(r[0]), level=r[1], experience=r[2],
                practiced_count=r[3], unlocked=bool(r[4]), last_practiced=r[5],
            )
            for r in rows
        ]

    def list_unlocked_skills(self, agent_id: str) -> List[SkillType]:
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT skill_type FROM skill_mastery WHERE agent_id = ? AND unlocked = 1",
            (agent_id,)
        ).fetchall()
        return [SkillType(r[0]) for r in rows]

    def insert_milestone(self, milestone_id: str, name: str, achieved_by: str,
                         generation: int, bonus: float = 1.0):
        cur = self._conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO civilization_milestone
                (milestone_id, name, achieved_by, generation, achieved_at, global_bonus)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (milestone_id, name, achieved_by, generation, time.time(), bonus))
        self._conn.commit()

    def list_milestones(self) -> List[Dict]:
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT milestone_id, name, achieved_by, generation, achieved_at, global_bonus "
            "FROM civilization_milestone ORDER BY achieved_at"
        ).fetchall()
        return [{
            'milestone_id': r[0], 'name': r[1], 'achieved_by': r[2],
            'generation': r[3], 'achieved_at': r[4], 'global_bonus': r[5],
        } for r in rows]

    def insert_innovation(self, innovation_id: str, agent_id: str, innovation_type: str,
                          description: str, generation: int, complexity_level: int,
                          impact_score: float):
        cur = self._conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO innovation_record
                (innovation_id, agent_id, innovation_type, description, generation,
                 complexity_level, impact_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (innovation_id, agent_id, innovation_type, description, generation,
              complexity_level, impact_score, time.time()))
        self._conn.commit()

    def list_innovations(self, limit: int = 50) -> List[Dict]:
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT innovation_id, agent_id, innovation_type, description, generation, "
            "complexity_level, impact_score, created_at "
            "FROM innovation_record ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [{
            'innovation_id': r[0], 'agent_id': r[1], 'innovation_type': r[2],
            'description': r[3], 'generation': r[4], 'complexity_level': r[5],
            'impact_score': r[6], 'created_at': r[7],
        } for r in rows]

    def get_statistics(self) -> Dict:
        cur = self._conn.cursor()
        stats = {}
        # 技能统计
        row = cur.execute(
            "SELECT COUNT(DISTINCT agent_id), COUNT(*), AVG(level), "
            "SUM(CASE WHEN unlocked = 1 THEN 1 ELSE 0 END) FROM skill_mastery"
        ).fetchone()
        stats['agents_with_skills'] = row[0] if row[0] else 0
        stats['total_skill_records'] = row[1] if row[1] else 0
        stats['avg_skill_level'] = round(row[2], 2) if row[2] else 0
        stats['unlocked_skills'] = row[3] if row[3] else 0
        # 复杂度统计
        row = cur.execute(
            "SELECT AVG(complexity_level), MAX(complexity_level), "
            "AVG(meta_learning_factor), SUM(innovation_count) FROM complexity_profile"
        ).fetchone()
        stats['avg_complexity'] = round(row[0], 2) if row[0] else 0
        stats['max_complexity'] = row[1] if row[1] else 0
        stats['avg_meta_learning'] = round(row[2], 3) if row[2] else 0
        stats['total_innovations'] = row[3] if row[3] else 0
        # 文明里程碑
        row = cur.execute("SELECT COUNT(*), SUM(global_bonus) FROM civilization_milestone").fetchone()
        stats['milestones_achieved'] = row[0] if row[0] else 0
        stats['total_civilization_bonus'] = round(row[1], 2) if row[1] else 1.0
        return stats


# ============================================================
# ⚡ 复杂度引擎
# ============================================================

class ComplexityEngine:
    """
    复杂度引擎 - 管理Agent技能发展和文明进步

    核心能力：
    1. 技能树解锁（基于前置条件）
    2. 经验积累与升级
    3. 元学习加速
    4. 文明里程碑检测
    5. 创新记录
    """

    def __init__(self, db: ComplexityDB = None, data_dir: str = None):
        self.data_dir = data_dir or os.environ.get(
            "CITY_STATE_DATA_DIR",
            r"C:\Users\dfhai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a45044b9f3d6718577ed1f8\city_state_data\ecosystem"
        )
        if db:
            self.db = db
        else:
            db_path = os.path.join(self.data_dir, "state", "complexity.db")
            self.db = ComplexityDB(db_path)
        self._interlock_cbs: List[callable] = []  # 支持多回调，避免覆盖
        logger.info("ComplexityEngine initialized")

    def register_interlock(self, callback: callable):
        """注册互锁回调（支持多回调，不再覆盖）"""
        self._interlock_cbs.append(callback)

    def _emit_interlock(self, source: str, event_type: str, data: Dict):
        for cb in self._interlock_cbs:
            try:
                cb(source, event_type, data)
            except Exception as e:
                logger.warning(f"Interlock emit failed: {e}")

    def create_profile(self, agent_id: str, generation: int = 0,
                       cognitive_traits: Dict = None) -> ComplexityProfile:
        """创建Agent的复杂度画像"""
        profile = ComplexityProfile(
            agent_id=agent_id,
            generation=generation,
            cognitive_traits=cognitive_traits or {},
        )
        self.db.upsert_profile(profile)
        return profile

    def practice_skill(self, agent_id: str, skill_type: SkillType,
                       amount: float = 1.0, meta_learning_factor: float = 1.0) -> Dict:
        """
        练习技能
        - 元学习加速：meta_learning_factor > 1 时加速经验获取
        - 等级提升后解锁新技能
        """
        skill = self.db.get_skill(agent_id, skill_type)
        if not skill:
            skill = SkillMastery(skill_type=skill_type)

        # 元学习加速
        effective_amount = amount * meta_learning_factor
        leveled_up = skill.gain_experience(effective_amount)
        self.db.upsert_skill(agent_id, skill)

        # 检查是否解锁新技能
        unlocked_new = self._check_skill_unlocks(agent_id)

        # 更新画像
        self._recalculate_profile(agent_id)

        return {
            'skill_type': skill_type.value,
            'new_level': round(skill.level, 2),
            'leveled_up': leveled_up,
            'newly_unlocked': [s.value for s in unlocked_new],
        }

    def _check_skill_unlocks(self, agent_id: str) -> List[SkillType]:
        """检查并解锁满足前置条件的技能"""
        unlocked = []
        current_skills = set(self.db.list_unlocked_skills(agent_id))
        for skill_type, prereqs in SKILL_PREREQUISITES.items():
            if skill_type in current_skills:
                continue
            # 检查前置条件
            if all(p in current_skills for p in prereqs):
                # 自动解锁新技能
                skill = self.db.get_skill(agent_id, skill_type)
                if not skill:
                    skill = SkillMastery(skill_type=skill_type, unlocked=True)
                else:
                    skill.unlocked = True
                self.db.upsert_skill(agent_id, skill)
                unlocked.append(skill_type)
                logger.info(f"Agent {agent_id} unlocked skill: {skill_type.value}")
        return unlocked

    def _recalculate_profile(self, agent_id: str):
        """重新计算Agent的复杂度画像"""
        skills = self.db.list_agent_skills(agent_id)
        unlocked = [s for s in skills if s.unlocked]
        profile = self.db.get_profile(agent_id)
        if not profile:
            profile = ComplexityProfile(agent_id=agent_id)

        # 计算总技能值
        total_value = sum(SKILL_COMPLEXITY_VALUE.get(s.skill_type, 1) for s in unlocked)
        profile.total_skill_value = total_value
        profile.skills_mastered = len([s for s in unlocked if s.level >= MASTERY_THRESHOLD])
        profile.complexity_level = profile.update_complexity()

        # 元学习因子：基于ANALYSIS和META_LEARNING技能等级
        analysis_skill = next((s for s in skills if s.skill_type == SkillType.ANALYSIS), None)
        meta_skill = next((s for s in skills if s.skill_type == SkillType.META_LEARNING), None)
        if analysis_skill and meta_skill:
            profile.meta_learning_factor = 1.0 + (analysis_skill.level / 100) * 0.3 + (meta_skill.level / 100) * 0.7

        self.db.upsert_profile(profile)
        return profile

    def learn_skill_from_agent(self, learner_id: str, teacher_id: str,
                               skill_type: SkillType) -> Optional[Dict]:
        """社会学习 - 从其他Agent学习技能"""
        teacher_skill = self.db.get_skill(teacher_id, skill_type)
        if not teacher_skill or not teacher_skill.unlocked:
            return None

        learner_skill = self.db.get_skill(learner_id, skill_type)
        if not learner_skill:
            learner_skill = SkillMastery(skill_type=skill_type, unlocked=True)

        # 从教师获得经验（学习效率 = 教师等级 * 0.1）
        transfer_amount = teacher_skill.level * 0.1
        leveled_up = learner_skill.gain_experience(transfer_amount)
        self.db.upsert_skill(learner_id, learner_skill)

        # 更新知识传递计数
        teacher_profile = self.db.get_profile(teacher_id)
        if teacher_profile:
            teacher_profile.knowledge_transfer_count += 1
            self.db.upsert_profile(teacher_profile)

        # 更新学习者的复杂度画像
        self._recalculate_profile(learner_id)

        # 互锁通知
        self._emit_interlock("complexity", "knowledge_transfer", {
            'learner_id': learner_id,
            'teacher_id': teacher_id,
            'skill_type': skill_type.value,
            'amount': round(transfer_amount, 2),
        })

        return {
            'skill_type': skill_type.value,
            'new_level': round(learner_skill.level, 2),
            'teacher_level': round(teacher_skill.level, 2),
            'transferred': round(transfer_amount, 2),
        }

    def check_civilization_milestones(self, agent_id: str, generation: int) -> List[Dict]:
        """检测文明级里程碑达成"""
        achieved = []
        existing = {m['milestone_id'] for m in self.db.list_milestones()}
        unlocked_skills = set(self.db.list_unlocked_skills(agent_id))

        for mid, info in CIVILIZATION_MILESTONES.items():
            if mid in existing:
                continue
            required = set(info['required_skills'])
            if required.issubset(unlocked_skills):
                self.db.insert_milestone(mid, info['name'], agent_id, generation, info['bonus'])
                achieved.append({
                    'milestone_id': mid,
                    'name': info['name'],
                    'bonus': info['bonus'],
                    'generation': generation,
                })
                self._emit_interlock("complexity", "milestone_achieved", {
                    'milestone_id': mid,
                    'name': info['name'],
                    'achieved_by': agent_id,
                    'generation': generation,
                })
                logger.info(f"Civilization milestone achieved: {info['name']} by {agent_id}")
        return achieved

    def create_innovation(self, agent_id: str, innovation_type: str,
                          description: str, generation: int,
                          impact_score: float = 1.0) -> str:
        """记录创新"""
        profile = self.db.get_profile(agent_id)
        complexity = profile.complexity_level if profile else 0
        inno_id = hashlib.md5(f"{agent_id}{description}{time.time()}".encode()).hexdigest()[:12]
        self.db.insert_innovation(inno_id, agent_id, innovation_type, description,
                                   generation, complexity, impact_score)
        if profile:
            profile.innovation_count += 1
            self.db.upsert_profile(profile)
        self._emit_interlock("complexity", "innovation_created", {
            'innovation_id': inno_id,
            'agent_id': agent_id,
            'type': innovation_type,
            'generation': generation,
            'complexity': complexity,
        })
        return inno_id

    def get_skill_path_to_super_intelligence(self, agent_id: str) -> List[Dict]:
        """获取通往超级智能体的推荐学习路径"""
        try:
            unlocked = set(self.db.list_unlocked_skills(agent_id))
        except Exception as e:
            logger.warning(f"Failed to get unlocked skills for {agent_id}: {e}")
            return [{'status': 'error', 'message': '无法获取技能列表'}]

        target = SkillType.CREATIVITY
        if target in unlocked:
            return [{'status': 'completed', 'message': '已达成超级智能条件！'}]

        # BFS寻找学习路径（添加最大迭代限制防止无限循环）
        path = []
        visited = set(unlocked)
        queue = [(target, [])]
        max_iterations = 100  # 防止无限循环
        iterations = 0

        while queue and iterations < max_iterations:
            iterations += 1
            current, trail = queue.pop(0)
            prereqs = SKILL_PREREQUISITES.get(current, [])
            for p in prereqs:
                if p not in visited:
                    visited.add(p)  # 标记已访问，防止重复处理
                    new_trail = trail + [current]
                    if p in unlocked:
                        path = new_trail
                        break
                    queue.append((p, new_trail))
            if path:
                break

        if iterations >= max_iterations:
            logger.warning(f"BFS exceeded max iterations for {agent_id}")

        if not path:
            # 推荐最基础的未解锁技能
            for s in [SkillType.GATHERING, SkillType.SCOUTING, SkillType.CRAFTING, SkillType.INNOVATION]:
                if s not in unlocked:
                    path = [s]
                    break

        return [
            {'step': i, 'skill': s.value, 'status': 'locked' if s not in unlocked else 'unlocked'}
            for i, s in enumerate(path)
        ]

    def get_statistics(self) -> Dict:
        return self.db.get_statistics()

    def close(self):
        self.db.close()


# ============================================================
# 工厂函数
# ============================================================

def create_default_complexity(data_dir: str = None) -> ComplexityEngine:
    """创建默认复杂度引擎"""
    return ComplexityEngine(data_dir=data_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    print("=== 复杂度分层系统冒烟测试 ===")
    engine = create_default_complexity()

    # 创建Agent
    agent_id = "agent_001"
    engine.create_profile(agent_id, generation=1)
    print(f"\n--- 创建Agent: {agent_id} ---")

    # 练习基础技能
    print("\n--- 练习技能 ---")
    for _ in range(10):
        result = engine.practice_skill(agent_id, SkillType.GATHERING, amount=5.0)
    print(f"  GATHERING: level={result['new_level']}, unlocked={result['newly_unlocked']}")

    for _ in range(8):
        result = engine.practice_skill(agent_id, SkillType.SCOUTING, amount=5.0)
    print(f"  SCOUTING: level={result['new_level']}, unlocked={result['newly_unlocked']}")

    # 练习制造（需要GATHERING前置）
    for _ in range(6):
        result = engine.practice_skill(agent_id, SkillType.CRAFTING, amount=4.0)
    print(f"  CRAFTING: level={result['new_level']}, unlocked={result['newly_unlocked']}")

    # 练习创新（需要CRAFTING+SCOUTING前置）
    for _ in range(5):
        result = engine.practice_skill(agent_id, SkillType.INNOVATION, amount=3.0)
    print(f"  INNOVATION: level={result['new_level']}, unlocked={result['newly_unlocked']}")

    # 查看复杂度
    profile = engine.db.get_profile(agent_id)
    levels = ["L0-刺激反应", "L1-经验学习", "L2-规划", "L3-元认知", "L4-创造性", "L5-超级智能"]
    print(f"\n--- 当前状态 ---")
    print(f"  复杂度等级: {levels[profile.complexity_level]}")
    print(f"  总技能值: {profile.total_skill_value}")
    print(f"  元学习因子: {profile.meta_learning_factor}")
    print(f"  掌握技能数: {profile.skills_mastered}")

    # 文明里程碑
    print(f"\n--- 文明里程碑检测 ---")
    milestones = engine.check_civilization_milestones(agent_id, 1)
    for m in milestones:
        print(f"  达成: {m['name']} (加成x{m['bonus']})")

    # 创建创新
    print(f"\n--- 记录创新 ---")
    inno_id = engine.create_innovation(agent_id, "tool", "发明了石斧", 1, 2.0)
    print(f"  创新记录: {inno_id}")

    # 学习路径推荐
    print(f"\n--- 通往超级智能体的路径 ---")
    path = engine.get_skill_path_to_super_intelligence(agent_id)
    for step in path:
        print(f"  {step}")

    # 最终统计
    print(f"\n--- 最终统计 ---")
    stats = engine.get_statistics()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    engine.close()
    print("\n✅ 复杂度系统冒烟测试通过")
