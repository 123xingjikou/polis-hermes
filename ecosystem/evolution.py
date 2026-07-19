"""
🧬 城邦生态 - 进化系统 (Evolution System)
=========================================

在 polis_v3.py 生物进化基础上，增加认知进化机制：
- 基因增强：学习率/记忆容量/规划深度/元认知/社会认知
- 代际知识继承
- 智能商数 (IQ) 追踪
- 复杂度分层 (L0→L5 通往超级智能体)

设计原则：
- 独立数据库（evolution.db）
- 与 polis_v3.py 协同：读取其基因数据，增强认知维度
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
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum

logger = logging.getLogger('polis.evolution')


# ============================================================
# 🎯 基础定义
# ============================================================

class CognitiveTrait(Enum):
    """认知特质 - 超越基础基因的进化维度"""
    LEARNING_RATE = "learning_rate"
    MEMORY_CAPACITY = "memory_capacity"
    PLANNING_DEPTH = "planning_depth"
    META_LEARNING = "meta_learning"
    SOCIAL_COGNITION = "social_cognition"
    CREATIVITY = "creativity"
    ABSTRACT_REASONING = "abstract_reasoning"
    EMOTIONAL_INTELLIGENCE = "emotional_intelligence"


class ComplexityLevel(Enum):
    """复杂度分层 - 通往超级智能体的阶梯"""
    LVL0_REACTIVE = 0        # 刺激-反应
    LVL1_ADAPTIVE = 1        # 经验学习
    LVL2_PLANNING = 2        # 多步规划
    LVL3_META_COGNITIVE = 3  # 元认知（学习如何学习）
    LVL4_CREATIVE = 4        # 创造性思维
    LVL5_SUPER_INTELLIGENT = 5  # 超级智能


# 认知特质初始范围
COGNITIVE_RANGES = {
    CognitiveTrait.LEARNING_RATE: (0.1, 1.0),
    CognitiveTrait.MEMORY_CAPACITY: (50, 200),
    CognitiveTrait.PLANNING_DEPTH: (1, 5),
    CognitiveTrait.META_LEARNING: (0.0, 0.3),
    CognitiveTrait.SOCIAL_COGNITION: (0.1, 1.0),
    CognitiveTrait.CREATIVITY: (0.1, 0.8),
    CognitiveTrait.ABSTRACT_REASONING: (0.1, 0.8),
    CognitiveTrait.EMOTIONAL_INTELLIGENCE: (0.2, 1.0),
}

# 物种分类阈值 - 按认知特质偏好划分生态位
SPECIES_PROFILES = {
    "scholar": {
        "focus": ["learning_rate", "memory_capacity", "meta_learning"],
        "description": "学者型：专注学习与记忆",
    },
    "strategist": {
        "focus": ["planning_depth", "abstract_reasoning", "meta_learning"],
        "description": "战略型：长于规划与推理",
    },
    "diplomat": {
        "focus": ["social_cognition", "emotional_intelligence", "creativity"],
        "description": "外交型：擅长社交与情感",
    },
    "innovator": {
        "focus": ["creativity", "abstract_reasoning", "learning_rate"],
        "description": "创新型：创造与抽象并重",
    },
}

# 复杂度阈值 - IQ 达到此值晋级下一级
COMPLEXITY_THRESHOLDS = {
    ComplexityLevel.LVL0_REACTIVE: 0,
    ComplexityLevel.LVL1_ADAPTIVE: 30,
    ComplexityLevel.LVL2_PLANNING: 60,
    ComplexityLevel.LVL3_META_COGNITIVE: 100,
    ComplexityLevel.LVL4_CREATIVE: 140,
    ComplexityLevel.LVL5_SUPER_INTELLIGENT: 180,
}


@dataclass
class CognitiveGenome:
    """认知基因组 - Agent 的认知能力蓝图"""
    agent_id: str
    learning_rate: float = 0.3
    memory_capacity: float = 100.0
    planning_depth: int = 2
    meta_learning: float = 0.05
    social_cognition: float = 0.4
    creativity: float = 0.3
    abstract_reasoning: float = 0.3
    emotional_intelligence: float = 0.5
    iq_score: float = 50.0
    complexity_level: int = 0
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    mutation_history: List[Dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def calculate_iq(self) -> float:
        """
        计算智能商数 - 非线性涌现模型

        改进：从线性加权升级为认知交互模型
        - 基础维度：各认知特质的独立贡献
        - 交互维度：特质间的协同效应（涌现）
        - 瓶颈效应：最弱维度限制整体表现
        """
        # 1. 基础线性贡献
        base = (
            self.learning_rate * 12
            + self.memory_capacity * 0.08
            + self.planning_depth * 10
            + self.meta_learning * 40
            + self.social_cognition * 8
            + self.creativity * 12
            + self.abstract_reasoning * 12
            + self.emotional_intelligence * 6
        )

        # 2. 交互涌现效应（非线性）
        # 元认知放大学习率（学会学习 → 学习加速）
        synergy_meta_learn = self.meta_learning * self.learning_rate * 25
        # 社交认知 × 情商（社交智能协同）
        synergy_social = self.social_cognition * self.emotional_intelligence * 10
        # 创造力 × 抽象推理（创新思维协同）
        synergy_creative = self.creativity * self.abstract_reasoning * 12
        # 规划深度 × 抽象推理（战略思维涌现）
        synergy_planning = self.planning_depth * self.abstract_reasoning * 3
        # 记忆容量 × 学习率（经验积累加速）
        synergy_memory = (self.memory_capacity / 100) * self.learning_rate * 5

        synergy = (synergy_meta_learn + synergy_social + synergy_creative
                   + synergy_planning + synergy_memory)

        # 3. 瓶颈效应：最弱维度拖累整体（木桶原理）
        normalized_traits = [
            self.learning_rate / 1.0,       # 归一化到 [0,1]
            self.memory_capacity / 200.0,
            self.planning_depth / 5.0,
            self.meta_learning / 0.3,
            self.social_cognition / 1.0,
            self.creativity / 0.8,
            self.abstract_reasoning / 0.8,
            self.emotional_intelligence / 1.0,
        ]
        min_trait = min(normalized_traits)
        # 瓶颈惩罚：最弱维度低于 0.3 时开始惩罚
        bottleneck_penalty = max(0, (0.3 - min_trait) * 20) if min_trait < 0.3 else 0

        iq = base + synergy - bottleneck_penalty
        self.iq_score = round(max(0, iq), 2)
        return self.iq_score

    def get_complexity_level(self) -> ComplexityLevel:
        """根据 IQ 确定复杂度等级"""
        iq = self.calculate_iq()
        level = ComplexityLevel.LVL0_REACTIVE
        for lvl in ComplexityLevel:
            threshold = COMPLEXITY_THRESHOLDS.get(lvl, 0)
            if iq >= threshold:
                level = lvl
        self.complexity_level = level.value
        return level

    def mutate(self, rate: float = 0.15, stress_factor: float = 1.0,
               beneficial_bias: float = 0.3) -> 'CognitiveGenome':
        """
        认知基因突变 - 压力越大突变率越高

        改进：方向性突变
        - beneficial_bias > 0 时，突变偏向有利方向（向高值偏移）
        - 压力越大，有利偏移越强（逆境驱动进化）
        """
        def mutate_trait(value: float, trait: CognitiveTrait) -> float:
            low, high = COGNITIVE_RANGES.get(trait, (0.0, 1.0))
            effective_rate = min(0.8, rate * stress_factor)  # 上限80%防失控
            if random.random() < effective_rate:
                spread = (high - low) * 0.15  # 缩小扰动幅度 0.2→0.15
                # 方向性：有利偏移概率 = 基础偏置 + 压力奖励
                up_prob = min(0.75, 0.5 + beneficial_bias * stress_factor * 0.1)
                if random.random() < up_prob:
                    delta = random.uniform(0, spread)  # 向有利方向
                else:
                    delta = random.uniform(-spread, 0)  # 向不利方向
                return max(low, min(high, value + delta))
            return value

        def mutate_int(value: int, trait: CognitiveTrait) -> int:
            low, high = COGNITIVE_RANGES.get(trait, (1, 10))
            if isinstance(low, float):
                low = int(low)
            if isinstance(high, float):
                high = int(high)
            if random.random() < min(0.8, rate * stress_factor):
                up_prob = min(0.75, 0.5 + beneficial_bias * stress_factor * 0.1)
                if random.random() < up_prob:
                    delta = random.randint(0, 1)
                else:
                    delta = random.randint(-1, 0)
                return max(low, min(high, value + delta))
            return value

        mutated = CognitiveGenome(
            agent_id=self.agent_id,
            learning_rate=mutate_trait(self.learning_rate, CognitiveTrait.LEARNING_RATE),
            memory_capacity=mutate_trait(self.memory_capacity, CognitiveTrait.MEMORY_CAPACITY),
            planning_depth=mutate_int(self.planning_depth, CognitiveTrait.PLANNING_DEPTH),
            meta_learning=mutate_trait(self.meta_learning, CognitiveTrait.META_LEARNING),
            social_cognition=mutate_trait(self.social_cognition, CognitiveTrait.SOCIAL_COGNITION),
            creativity=mutate_trait(self.creativity, CognitiveTrait.CREATIVITY),
            abstract_reasoning=mutate_trait(self.abstract_reasoning, CognitiveTrait.ABSTRACT_REASONING),
            emotional_intelligence=mutate_trait(self.emotional_intelligence, CognitiveTrait.EMOTIONAL_INTELLIGENCE),
            generation=self.generation,
            parent_ids=list(self.parent_ids),
            mutation_history=list(self.mutation_history),
        )
        mutated.calculate_iq()
        mutated.get_complexity_level()
        return mutated

    @classmethod
    def crossover(cls, parent_a: 'CognitiveGenome', parent_b: 'CognitiveGenome',
                  child_id: str, generation: int) -> 'CognitiveGenome':
        """
        认知基因交叉 - 有性繁殖

        改进：加权混合替代二选一
        - 按 IQ 权重混合父母基因，高 IQ 方向贡献更大
        - 加入小幅随机扰动保持多样性
        """
        # 按父母 IQ 计算混合权重（IQ 越高贡献越大）
        iq_sum = parent_a.iq_score + parent_b.iq_score
        if iq_sum <= 0:
            w_a = 0.5
        else:
            w_a = parent_a.iq_score / iq_sum
        w_b = 1.0 - w_a

        def blend(a, b):
            """加权混合 + 小幅随机扰动"""
            base = a * w_a + b * w_b
            jitter = (random.random() - 0.5) * abs(a - b) * 0.1  # 10% 抖动
            return base + jitter

        def blend_int(a, b):
            """整数混合：按概率选父母，偏向高 IQ 方"""
            if random.random() < w_a:
                return a
            return b

        child = cls(
            agent_id=child_id,
            learning_rate=blend(parent_a.learning_rate, parent_b.learning_rate),
            memory_capacity=blend(parent_a.memory_capacity, parent_b.memory_capacity),
            planning_depth=blend_int(parent_a.planning_depth, parent_b.planning_depth),
            meta_learning=blend(parent_a.meta_learning, parent_b.meta_learning),
            social_cognition=blend(parent_a.social_cognition, parent_b.social_cognition),
            creativity=blend(parent_a.creativity, parent_b.creativity),
            abstract_reasoning=blend(parent_a.abstract_reasoning, parent_b.abstract_reasoning),
            emotional_intelligence=blend(parent_a.emotional_intelligence, parent_b.emotional_intelligence),
            generation=generation,
            parent_ids=[parent_a.agent_id, parent_b.agent_id],
        )
        child.calculate_iq()
        child.get_complexity_level()
        return child

    @classmethod
    def random(cls, agent_id: str, generation: int = 0) -> 'CognitiveGenome':
        """随机生成认知基因组"""
        def rand_range(low, high):
            return random.uniform(low, high)

        low_lr, high_lr = COGNITIVE_RANGES[CognitiveTrait.LEARNING_RATE]
        low_mc, high_mc = COGNITIVE_RANGES[CognitiveTrait.MEMORY_CAPACITY]
        low_pd, high_pd = COGNITIVE_RANGES[CognitiveTrait.PLANNING_DEPTH]
        low_ml, high_ml = COGNITIVE_RANGES[CognitiveTrait.META_LEARNING]
        low_sc, high_sc = COGNITIVE_RANGES[CognitiveTrait.SOCIAL_COGNITION]
        low_cr, high_cr = COGNITIVE_RANGES[CognitiveTrait.CREATIVITY]
        low_ar, high_ar = COGNITIVE_RANGES[CognitiveTrait.ABSTRACT_REASONING]
        low_ei, high_ei = COGNITIVE_RANGES[CognitiveTrait.EMOTIONAL_INTELLIGENCE]

        genome = cls(
            agent_id=agent_id,
            learning_rate=rand_range(low_lr, high_lr),
            memory_capacity=rand_range(low_mc, high_mc),
            planning_depth=random.randint(int(low_pd), int(high_pd)),
            meta_learning=rand_range(low_ml, high_ml),
            social_cognition=rand_range(low_sc, high_sc),
            creativity=rand_range(low_cr, high_cr),
            abstract_reasoning=rand_range(low_ar, high_ar),
            emotional_intelligence=rand_range(low_ei, high_ei),
            generation=generation,
        )
        genome.calculate_iq()
        genome.get_complexity_level()
        return genome

    def to_dict(self) -> Dict:
        return {
            'agent_id': self.agent_id,
            'learning_rate': round(self.learning_rate, 4),
            'memory_capacity': round(self.memory_capacity, 2),
            'planning_depth': self.planning_depth,
            'meta_learning': round(self.meta_learning, 4),
            'social_cognition': round(self.social_cognition, 4),
            'creativity': round(self.creativity, 4),
            'abstract_reasoning': round(self.abstract_reasoning, 4),
            'emotional_intelligence': round(self.emotional_intelligence, 4),
            'iq_score': self.iq_score,
            'complexity_level': self.complexity_level,
            'generation': self.generation,
            'parent_ids': self.parent_ids,
        }

    def classify_species(self) -> str:
        """
        根据认知特质偏好划分物种生态位

        返回物种类型，用于多样性维护和生态位选择
        """
        scores = {}
        for species, profile in SPECIES_PROFILES.items():
            # 计算该物种关注特质的归一化得分之和
            trait_sum = 0.0
            for trait_name in profile["focus"]:
                value = getattr(self, trait_name, 0)
                low, high = COGNITIVE_RANGES.get(
                    CognitiveTrait(trait_name) if trait_name in [t.value for t in CognitiveTrait] else CognitiveTrait.LEARNING_RATE,
                    (0, 1)
                )
                # 归一化到 [0, 1]
                normalized = (value - low) / (high - low) if high > low else 0
                trait_sum += max(0, min(1, normalized))
            scores[species] = trait_sum / len(profile["focus"])
        return max(scores, key=scores.get)


@dataclass
class GenerationRecord:
    """代际记录 - 追踪每一代的关键指标"""
    generation: int
    population: int
    avg_iq: float
    max_iq: float
    min_iq: float
    avg_complexity: float
    max_complexity: int
    dominant_trait: str
    birth_count: int
    death_count: int
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 🗄️ 数据库层
# ============================================================

class EvolutionDB:
    """进化系统数据库"""

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
        logger.info(f"EvolutionDB initialized: {self.db_path}")

    def _create_tables(self):
        cur = self._conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cognitive_genome (
                agent_id TEXT PRIMARY KEY,
                learning_rate REAL NOT NULL,
                memory_capacity REAL NOT NULL,
                planning_depth INTEGER NOT NULL,
                meta_learning REAL NOT NULL,
                social_cognition REAL NOT NULL,
                creativity REAL NOT NULL,
                abstract_reasoning REAL NOT NULL,
                emotional_intelligence REAL NOT NULL,
                iq_score REAL NOT NULL,
                complexity_level INTEGER NOT NULL,
                generation INTEGER NOT NULL,
                parent_ids TEXT DEFAULT '[]',
                mutation_history TEXT DEFAULT '[]',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS generation_record (
                generation INTEGER PRIMARY KEY,
                population INTEGER NOT NULL,
                avg_iq REAL NOT NULL,
                max_iq REAL NOT NULL,
                min_iq REAL NOT NULL,
                avg_complexity REAL NOT NULL,
                max_complexity INTEGER NOT NULL,
                dominant_trait TEXT NOT NULL,
                birth_count INTEGER NOT NULL,
                death_count INTEGER NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_pool (
                knowledge_id TEXT PRIMARY KEY,
                knowledge_type TEXT NOT NULL,
                content TEXT NOT NULL,
                creator_id TEXT NOT NULL,
                generation INTEGER NOT NULL,
                utility_score REAL DEFAULT 0.5,
                usage_count INTEGER DEFAULT 0,
                inherited_count INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_gen_type
                ON knowledge_pool(generation, knowledge_type)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_genome_iq
                ON cognitive_genome(iq_score DESC)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_genome_complexity
                ON cognitive_genome(complexity_level DESC)
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

    def upsert_genome(self, genome: CognitiveGenome):
        cur = self._conn.cursor()
        now = time.time()
        cur.execute("""
            INSERT OR REPLACE INTO cognitive_genome
                (agent_id, learning_rate, memory_capacity, planning_depth,
                 meta_learning, social_cognition, creativity, abstract_reasoning,
                 emotional_intelligence, iq_score, complexity_level, generation,
                 parent_ids, mutation_history, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            genome.agent_id, genome.learning_rate, genome.memory_capacity,
            genome.planning_depth, genome.meta_learning, genome.social_cognition,
            genome.creativity, genome.abstract_reasoning, genome.emotional_intelligence,
            genome.iq_score, genome.complexity_level, genome.generation,
            json.dumps(genome.parent_ids), json.dumps(genome.mutation_history),
            genome.created_at, now,
        ))
        self._conn.commit()

    def get_genome(self, agent_id: str) -> Optional[CognitiveGenome]:
        cur = self._conn.cursor()
        row = cur.execute(
            "SELECT agent_id, learning_rate, memory_capacity, planning_depth, "
            "meta_learning, social_cognition, creativity, abstract_reasoning, "
            "emotional_intelligence, iq_score, complexity_level, generation, "
            "parent_ids, mutation_history, created_at "
            "FROM cognitive_genome WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        if not row:
            return None
        try:
            parents = json.loads(row[12]) if row[12] else []
        except (json.JSONDecodeError, IndexError):
            parents = []
        try:
            mutations = json.loads(row[13]) if row[13] else []
        except (json.JSONDecodeError, IndexError):
            mutations = []
        return CognitiveGenome(
            agent_id=row[0],
            learning_rate=row[1],
            memory_capacity=row[2],
            planning_depth=row[3],
            meta_learning=row[4],
            social_cognition=row[5],
            creativity=row[6],
            abstract_reasoning=row[7],
            emotional_intelligence=row[8],
            iq_score=row[9],
            complexity_level=row[10],
            generation=row[11],
            parent_ids=parents,
            mutation_history=mutations,
            created_at=row[14] if len(row) > 14 else 0,
        )

    def list_genomes(self, limit: int = 100, order_by: str = "iq_score DESC") -> List[CognitiveGenome]:
        cur = self._conn.cursor()
        allowed_orders = {"iq_score DESC", "iq_score ASC", "complexity_level DESC",
                         "generation DESC", "created_at DESC"}
        if order_by not in allowed_orders:
            order_by = "iq_score DESC"
        rows = cur.execute(
            f"SELECT agent_id, learning_rate, memory_capacity, planning_depth, "
            f"meta_learning, social_cognition, creativity, abstract_reasoning, "
            f"emotional_intelligence, iq_score, complexity_level, generation, "
            f"parent_ids, mutation_history, created_at "
            f"FROM cognitive_genome ORDER BY {order_by} LIMIT ?",
            (limit,)
        ).fetchall()
        genomes = []
        for row in rows:
            try:
                parents = json.loads(row[12]) if row[12] else []
            except (json.JSONDecodeError, IndexError):
                parents = []
            try:
                mutations = json.loads(row[13]) if row[13] else []
            except (json.JSONDecodeError, IndexError):
                mutations = []
            genomes.append(CognitiveGenome(
                agent_id=row[0], learning_rate=row[1], memory_capacity=row[2],
                planning_depth=row[3], meta_learning=row[4], social_cognition=row[5],
                creativity=row[6], abstract_reasoning=row[7], emotional_intelligence=row[8],
                iq_score=row[9], complexity_level=row[10], generation=row[11],
                parent_ids=parents, mutation_history=mutations,
                created_at=row[14] if len(row) > 14 else 0,
            ))
        return genomes

    def get_genomes_batch(self, agent_ids: List[str]) -> Dict[str, CognitiveGenome]:
        """批量获取多个 Agent 的基因组（解决 N+1 查询问题）"""
        if not agent_ids:
            return {}
        placeholders = ",".join("?" * len(agent_ids))
        cur = self._conn.cursor()
        rows = cur.execute(
            f"SELECT agent_id, learning_rate, memory_capacity, planning_depth, "
            f"meta_learning, social_cognition, creativity, abstract_reasoning, "
            f"emotional_intelligence, iq_score, complexity_level, generation, "
            f"parent_ids, mutation_history, created_at "
            f"FROM cognitive_genome WHERE agent_id IN ({placeholders})",
            agent_ids
        ).fetchall()
        result = {}
        for row in rows:
            try:
                parents = json.loads(row[12]) if row[12] else []
            except (json.JSONDecodeError, IndexError):
                parents = []
            try:
                mutations = json.loads(row[13]) if row[13] else []
            except (json.JSONDecodeError, IndexError):
                mutations = []
            result[row[0]] = CognitiveGenome(
                agent_id=row[0], learning_rate=row[1], memory_capacity=row[2],
                planning_depth=row[3], meta_learning=row[4], social_cognition=row[5],
                creativity=row[6], abstract_reasoning=row[7], emotional_intelligence=row[8],
                iq_score=row[9], complexity_level=row[10], generation=row[11],
                parent_ids=parents, mutation_history=mutations,
                created_at=row[14] if len(row) > 14 else 0,
            )
        return result

    def count_genomes(self) -> int:
        cur = self._conn.cursor()
        row = cur.execute("SELECT COUNT(*) FROM cognitive_genome").fetchone()
        return row[0] if row else 0

    def delete_genome(self, agent_id: str):
        cur = self._conn.cursor()
        cur.execute("DELETE FROM cognitive_genome WHERE agent_id = ?", (agent_id,))
        self._conn.commit()

    def insert_generation_record(self, record: GenerationRecord):
        cur = self._conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO generation_record
                (generation, population, avg_iq, max_iq, min_iq, avg_complexity,
                 max_complexity, dominant_trait, birth_count, death_count, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.generation, record.population, record.avg_iq, record.max_iq,
            record.min_iq, record.avg_complexity, record.max_complexity,
            record.dominant_trait, record.birth_count, record.death_count,
            record.timestamp,
        ))
        self._conn.commit()

    def get_generation_record(self, generation: int) -> Optional[GenerationRecord]:
        cur = self._conn.cursor()
        row = cur.execute(
            "SELECT generation, population, avg_iq, max_iq, min_iq, avg_complexity, "
            "max_complexity, dominant_trait, birth_count, death_count, timestamp "
            "FROM generation_record WHERE generation = ?", (generation,)
        ).fetchone()
        if not row:
            return None
        return GenerationRecord(
            generation=row[0], population=row[1], avg_iq=row[2], max_iq=row[3],
            min_iq=row[4], avg_complexity=row[5], max_complexity=row[6],
            dominant_trait=row[7], birth_count=row[8], death_count=row[9],
            timestamp=row[10],
        )

    def list_generation_records(self, limit: int = 50) -> List[GenerationRecord]:
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT generation, population, avg_iq, max_iq, min_iq, avg_complexity, "
            "max_complexity, dominant_trait, birth_count, death_count, timestamp "
            "FROM generation_record ORDER BY generation DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [GenerationRecord(
            generation=r[0], population=r[1], avg_iq=r[2], max_iq=r[3],
            min_iq=r[4], avg_complexity=r[5], max_complexity=r[6],
            dominant_trait=r[7], birth_count=r[8], death_count=r[9],
            timestamp=r[10],
        ) for r in rows]

    def insert_knowledge(self, knowledge_id: str, knowledge_type: str,
                         content: str, creator_id: str, generation: int,
                         utility_score: float = 0.5):
        cur = self._conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO knowledge_pool
                (knowledge_id, knowledge_type, content, creator_id, generation,
                 utility_score, usage_count, inherited_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)
        """, (knowledge_id, knowledge_type, content, creator_id, generation,
              utility_score, time.time()))
        self._conn.commit()

    def get_knowledge_for_generation(self, generation: int, limit: int = 20) -> List[Dict]:
        """获取可继承的知识（前代高实用性知识）"""
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT knowledge_id, knowledge_type, content, creator_id, generation, "
            "utility_score, usage_count, inherited_count "
            "FROM knowledge_pool WHERE generation < ? ORDER BY utility_score DESC LIMIT ?",
            (generation, limit)
        ).fetchall()
        return [{
            'knowledge_id': r[0], 'knowledge_type': r[1], 'content': r[2],
            'creator_id': r[3], 'generation': r[4], 'utility_score': r[5],
            'usage_count': r[6], 'inherited_count': r[7],
        } for r in rows]

    def get_knowledge_count(self) -> int:
        cur = self._conn.cursor()
        row = cur.execute("SELECT COUNT(*) FROM knowledge_pool").fetchone()
        return row[0] if row else 0

    def increment_inherited_count(self, knowledge_id: str):
        """增加知识的继承计数"""
        cur = self._conn.cursor()
        cur.execute(
            "UPDATE knowledge_pool SET inherited_count = inherited_count + 1 "
            "WHERE knowledge_id = ?",
            (knowledge_id,)
        )
        self._conn.commit()

    def increment_usage_count(self, knowledge_id: str):
        """增加知识的使用计数"""
        cur = self._conn.cursor()
        cur.execute(
            "UPDATE knowledge_pool SET usage_count = usage_count + 1 "
            "WHERE knowledge_id = ?",
            (knowledge_id,)
        )
        self._conn.commit()

    def get_statistics(self) -> Dict:
        cur = self._conn.cursor()
        stats = {}
        # 基因组统计
        row = cur.execute(
            "SELECT COUNT(*), AVG(iq_score), MAX(iq_score), AVG(complexity_level), "
            "MAX(complexity_level) FROM cognitive_genome"
        ).fetchone()
        stats['genome_count'] = row[0] if row[0] else 0
        stats['avg_iq'] = round(row[1], 2) if row[1] else 0
        stats['max_iq'] = round(row[2], 2) if row[2] else 0
        stats['avg_complexity'] = round(row[3], 2) if row[3] else 0
        stats['max_complexity'] = row[4] if row[4] else 0
        # 代际统计
        row = cur.execute("SELECT COUNT(*), MAX(generation) FROM generation_record").fetchone()
        stats['total_generations'] = row[0] if row[0] else 0
        stats['latest_generation'] = row[1] if row[1] else 0
        # 知识统计
        stats['knowledge_count'] = self.get_knowledge_count()
        return stats


# ============================================================
# ⚡ 进化引擎
# ============================================================

class EvolutionEngine:
    """
    进化引擎 - 驱动认知进化循环

    核心流程：
    1. 选择：基于IQ和社会价值的繁殖选择
    2. 繁殖：交叉+突变产生后代
    3. 继承：前代知识传递给新生代
    4. 记录：保存代际指标
    """

    def __init__(self, db: EvolutionDB = None, data_dir: str = None):
        self.data_dir = data_dir or os.environ.get(
            "CITY_STATE_DATA_DIR",
            r"C:\Users\dfhai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a45044b9f3d6718577ed1f8\city_state_data\ecosystem"
        )
        if db:
            self.db = db
        else:
            db_path = os.path.join(self.data_dir, "state", "evolution.db")
            self.db = EvolutionDB(db_path)
        self._interlock_cb: Optional[callable] = None
        logger.info("EvolutionEngine initialized")

    def register_interlock(self, callback: callable):
        """注册互锁回调"""
        self._interlock_cb = callback

    def _emit_interlock(self, source: str, event_type: str, data: Dict):
        if self._interlock_cb:
            try:
                self._interlock_cb(source, event_type, data)
            except Exception as e:
                logger.warning(f"Interlock emit failed: {e}")

    def create_agent_genome(self, agent_id: str, generation: int = 0,
                           parent_ids: List[str] = None) -> CognitiveGenome:
        """为新Agent创建认知基因组"""
        genome = CognitiveGenome.random(agent_id, generation)
        if parent_ids:
            genome.parent_ids = parent_ids
        self.db.upsert_genome(genome)
        return genome

    def breed_agents(self, parent_a_id: str, parent_b_id: str,
                     child_id: str, generation: int,
                     stress_factor: float = 1.0) -> Optional[CognitiveGenome]:
        """
        繁殖两个Agent的后代
        流程：交叉 → 突变 → 计算IQ → 确定复杂度等级
        """
        parent_a = self.db.get_genome(parent_a_id)
        parent_b = self.db.get_genome(parent_b_id)
        if not parent_a or not parent_b:
            return None

        # 交叉
        child = CognitiveGenome.crossover(parent_a, parent_b, child_id, generation)

        # 突变（压力越大突变率越高）
        child = child.mutate(rate=0.15, stress_factor=stress_factor)

        # 记录突变历史
        child.mutation_history.append({
            'generation': generation,
            'parents': [parent_a_id, parent_b_id],
            'parent_avg_iq': (parent_a.iq_score + parent_b.iq_score) / 2,
            'child_iq': child.iq_score,
            'timestamp': time.time(),
        })

        self.db.upsert_genome(child)

        # 互锁通知
        self._emit_interlock("evolution", "agent_bred", {
            'child_id': child_id,
            'parent_ids': [parent_a_id, parent_b_id],
            'child_iq': child.iq_score,
            'child_complexity': child.complexity_level,
            'generation': generation,
        })

        return child

    def _calculate_diversity(self, genomes: List[CognitiveGenome]) -> float:
        """
        计算种群基因多样性（0=完全相同, 1=最大差异）

        使用各特质的标准差归一化值作为多样性指标
        """
        if len(genomes) < 2:
            return 0.0

        trait_names = ['learning_rate', 'memory_capacity', 'planning_depth',
                       'meta_learning', 'social_cognition', 'creativity',
                       'abstract_reasoning', 'emotional_intelligence']

        total_diversity = 0.0
        for trait in trait_names:
            values = [getattr(g, trait) for g in genomes]
            mean = sum(values) / len(values)
            if mean == 0:
                continue
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std = variance ** 0.5
            # 归一化：标准差 / 均值（变异系数）
            total_diversity += min(1.0, std / abs(mean)) if mean != 0 else 0

        return total_diversity / len(trait_names)

    def _select_by_niche(self, genomes: List[CognitiveGenome],
                         n_keep: int) -> Tuple[List[CognitiveGenome], List[CognitiveGenome]]:
        """
        生态位选择：确保每个物种都有代表保留

        改进传统精英选择：不仅保留最高 IQ，还保留各物种的最优个体
        防止单一物种垄断繁殖权
        """
        # 先按 IQ 全局排序
        genomes_sorted = sorted(genomes, key=lambda g: g.iq_score, reverse=True)

        # 按物种分组
        species_groups: Dict[str, List[CognitiveGenome]] = {}
        for g in genomes_sorted:
            species = g.classify_species()
            if species not in species_groups:
                species_groups[species] = []
            species_groups[species].append(g)

        # 每个物种至少保留 1 个代表（如果该物种有个体）
        elites = []
        remaining_slots = n_keep

        # 第一轮：每个物种保留最优个体
        for species, members in species_groups.items():
            if remaining_slots <= 0:
                break
            elites.append(members[0])
            remaining_slots -= 1

        # 第二轮：从全局排序中补充剩余名额
        elite_ids = {g.agent_id for g in elites}
        for g in genomes_sorted:
            if remaining_slots <= 0:
                break
            if g.agent_id not in elite_ids:
                elites.append(g)
                elite_ids.add(g.agent_id)
                remaining_slots -= 1

        # 保留的精英按 IQ 排序
        elites.sort(key=lambda g: g.iq_score, reverse=True)

        # 未保留的个体
        to_remove = [g for g in genomes if g.agent_id not in elite_ids]
        return elites, to_remove

    def _apply_baldwin_effect(self, genome: CognitiveGenome,
                              lifetime_learning: Dict[str, float]) -> CognitiveGenome:
        """
        鲍德温效应：终身学习影响进化方向

        Agent 在生命周期中习得的能力会逐渐内化为基因倾向
        - learning_bonus: 学习成果提升 learning_rate
        - social_bonus: 社交经验提升 social_cognition
        - creative_bonus: 创新实践提升 creativity
        """
        if not lifetime_learning:
            return genome

        # 学习成果内化（只有部分内化，避免拉马克主义）
        internalization_rate = 0.15  # 15% 的学习成果内化为基因

        if 'learning_progress' in lifetime_learning:
            bonus = lifetime_learning['learning_progress'] * internalization_rate
            low, high = COGNITIVE_RANGES[CognitiveTrait.LEARNING_RATE]
            genome.learning_rate = min(high, genome.learning_rate + bonus)

        if 'social_progress' in lifetime_learning:
            bonus = lifetime_learning['social_progress'] * internalization_rate
            low, high = COGNITIVE_RANGES[CognitiveTrait.SOCIAL_COGNITION]
            genome.social_cognition = min(high, genome.social_cognition + bonus)

        if 'creative_progress' in lifetime_learning:
            bonus = lifetime_learning['creative_progress'] * internalization_rate
            low, high = COGNITIVE_RANGES[CognitiveTrait.CREATIVITY]
            genome.creativity = min(high, genome.creativity + bonus)

        # 重新计算 IQ 和复杂度
        genome.calculate_iq()
        genome.get_complexity_level()
        return genome

    def evolve_generation(self, agent_ids: List[str], generation: int,
                          top_ratio: float = 0.4, stress_factor: float = 1.0,
                          lifetime_learning: Dict[str, Dict[str, float]] = None) -> Dict:
        """
        进化一代（增强版）

        流程：
        1. 批量获取基因组（N+1→1 查询）
        2. 鲍德温效应：应用终身学习成果
        3. 计算种群多样性，自适应调整突变率
        4. 生态位选择：确保多物种代表
        5. 精英保留 + 加权繁殖
        6. 知识继承与创造
        7. 记录代际指标
        """
        # 1. 批量获取基因组（解决 N+1 查询）
        genome_map = self.db.get_genomes_batch(agent_ids)
        genomes = list(genome_map.values())

        n = len(genomes)
        if n < 4:
            return {'error': '种群太小，无法进化', 'population': n}

        # 2. 鲍德温效应：应用终身学习成果
        if lifetime_learning:
            for aid, learning in lifetime_learning.items():
                if aid in genome_map:
                    genome_map[aid] = self._apply_baldwin_effect(genome_map[aid], learning)
                    self.db.upsert_genome(genome_map[aid])
            genomes = list(genome_map.values())

        # 3. 计算种群多样性，自适应调整突变率
        diversity = self._calculate_diversity(genomes)
        # 多样性低 → 提高突变率（防止早熟收敛）
        # 多样性高 → 降低突变率（保护已找到的优良组合）
        adaptive_rate = 0.15 * (1.0 + max(0, (0.15 - diversity)) * 5)  # 多样性<0.15时加速
        adaptive_rate = min(0.35, adaptive_rate)  # 上限 35%

        # 按IQ排序
        genomes.sort(key=lambda g: g.iq_score, reverse=True)

        # 4. 生态位选择
        n_keep = max(2, int(n * top_ratio))
        elites, to_remove = self._select_by_niche(genomes, n_keep)

        # 精英保留：Top 20% 个体基因受保护
        n_elite_protected = max(1, n_keep // 5)
        protected_elites = elites[:n_elite_protected]

        # 记录移除
        for g in to_remove:
            self.db.delete_genome(g.agent_id)

        # 5. 繁殖产生后代
        new_agents = []
        target_population = n
        current_count = len(elites)

        # 获取可继承知识
        inheritable_knowledge = self.db.get_knowledge_for_generation(generation, limit=10)

        while current_count < target_population and len(elites) >= 2:
            # 锦标赛选择（3选2），比纯加权随机更有利于多样性
            tournament_size = min(3, len(elites))
            candidates = random.sample(range(len(elites)), tournament_size)
            candidates.sort(key=lambda i: elites[i].iq_score, reverse=True)
            idx1 = candidates[0]
            idx2 = candidates[1] if len(candidates) > 1 else candidates[0]

            parent_a = elites[idx1]
            parent_b = elites[idx2]
            child_id = f"gen{generation}_{hashlib.md5(str(time.time() + random.random()).encode()).hexdigest()[:8]}"

            child = self.breed_agents(
                parent_a.agent_id, parent_b.agent_id,
                child_id, generation, stress_factor
            )
            if child:
                # 使用自适应突变率重新突变
                child = child.mutate(rate=adaptive_rate, stress_factor=stress_factor)
                child.calculate_iq()
                child.get_complexity_level()
                self.db.upsert_genome(child)
                new_agents.append(child)
                current_count += 1

                # 知识继承
                for knowledge in inheritable_knowledge:
                    self.db.increment_inherited_count(knowledge['knowledge_id'])

        # 6. 知识创造：高创造力精英产生新知识
        for elite in protected_elites:
            if elite.creativity > 0.6 and random.random() < 0.3:
                knowledge_content = f"gen{generation}_insight_by_{elite.agent_id}"
                self.create_knowledge(
                    creator_id=elite.agent_id,
                    knowledge_type="insight",
                    content=knowledge_content,
                    generation=generation,
                    utility_score=min(0.95, elite.creativity * 0.8 + 0.2)
                )

        # 计算代际指标
        remaining = self.db.list_genomes(limit=target_population)
        iq_scores = [g.iq_score for g in remaining]
        complexity_values = [g.complexity_level for g in remaining]
        avg_iq = sum(iq_scores) / len(iq_scores) if iq_scores else 0
        avg_complexity = sum(complexity_values) / len(complexity_values) if complexity_values else 0

        # 物种分布统计
        species_dist = {}
        for g in remaining:
            species = g.classify_species()
            species_dist[species] = species_dist.get(species, 0) + 1

        # 找出主导特质
        trait_totals = {t.value: 0.0 for t in CognitiveTrait}
        for g in remaining:
            for t in CognitiveTrait:
                trait_totals[t.value] += getattr(g, t.value, 0)
        dominant = max(trait_totals.items(), key=lambda x: x[1])[0] if trait_totals else "unknown"

        # 记录代际
        record = GenerationRecord(
            generation=generation,
            population=len(remaining),
            avg_iq=avg_iq,
            max_iq=max(iq_scores) if iq_scores else 0,
            min_iq=min(iq_scores) if iq_scores else 0,
            avg_complexity=avg_complexity,
            max_complexity=max(complexity_values) if complexity_values else 0,
            dominant_trait=dominant,
            birth_count=len(new_agents),
            death_count=len(to_remove),
        )
        self.db.insert_generation_record(record)

        # 互锁通知
        self._emit_interlock("evolution", "generation_evolved", {
            'generation': generation,
            'elites': len(elites),
            'new_born': len(new_agents),
            'removed': len(to_remove),
            'avg_iq': round(avg_iq, 2),
            'max_iq': round(max(iq_scores), 2) if iq_scores else 0,
            'avg_complexity': round(avg_complexity, 2),
            'diversity': round(diversity, 4),
            'mutation_rate': round(adaptive_rate, 4),
            'species_distribution': species_dist,
            'knowledge_inherited': len(inheritable_knowledge),
        })

        return {
            'generation': generation,
            'elites_kept': len(elites),
            'new_born': len(new_agents),
            'removed': len(to_remove),
            'avg_iq': round(avg_iq, 2),
            'max_iq': round(max(iq_scores), 2) if iq_scores else 0,
            'avg_complexity': round(avg_complexity, 2),
            'diversity': round(diversity, 4),
            'mutation_rate': round(adaptive_rate, 4),
            'species_distribution': species_dist,
            'dominant_trait': dominant,
            'knowledge_inherited': len(inheritable_knowledge),
        }

    def create_knowledge(self, creator_id: str, knowledge_type: str,
                         content: str, generation: int,
                         utility_score: float = 0.5) -> str:
        """创建新知识并加入知识池"""
        kid = hashlib.md5(f"{creator_id}{content}{time.time()}".encode()).hexdigest()[:12]
        self.db.insert_knowledge(kid, knowledge_type, content, creator_id, generation, utility_score)
        self._emit_interlock("evolution", "knowledge_created", {
            'knowledge_id': kid,
            'creator_id': creator_id,
            'generation': generation,
            'type': knowledge_type,
        })
        return kid

    def get_inheritable_knowledge(self, generation: int, limit: int = 20) -> List[Dict]:
        """获取可传递给下一代的高价值知识"""
        return self.db.get_knowledge_for_generation(generation, limit)

    def get_statistics(self) -> Dict:
        return self.db.get_statistics()

    def close(self):
        self.db.close()


# ============================================================
# 工厂函数
# ============================================================

def create_default_evolution(data_dir: str = None) -> EvolutionEngine:
    """创建默认进化引擎"""
    return EvolutionEngine(data_dir=data_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    print("=== 进化系统冒烟测试 ===")
    engine = create_default_evolution()

    # 创建初始种群
    print("\n--- 创建初始种群 (Gen 0) ---")
    n_agents = 10
    agent_ids = []
    for i in range(n_agents):
        aid = f"agent_{i:03d}"
        g = engine.create_agent_genome(aid, generation=0)
        agent_ids.append(aid)
        print(f"  {aid}: IQ={g.iq_score}, 复杂度=L{g.complexity_level}")

    # 进化多代
    print("\n--- 进化 20 代 ---")
    for gen in range(1, 21):
        result = engine.evolve_generation(agent_ids, gen, top_ratio=0.4, stress_factor=1.0 + gen * 0.03)
        if 'error' in result:
            print(f"  Gen {gen}: {result['error']}")
            break
        species_str = ", ".join(f"{k}:{v}" for k, v in result.get('species_distribution', {}).items())
        print(f"  Gen{gen:2d}: avg_iq={result['avg_iq']:6.2f}, max={result['max_iq']:6.2f}, "
              f"diversity={result.get('diversity', 0):.3f}, mut_rate={result.get('mutation_rate', 0):.3f}, "
              f"species=[{species_str}]")
        # 更新存活 agent_ids
        genomes = engine.db.list_genomes(limit=200)
        agent_ids = [g.agent_id for g in genomes]

    # 最终统计
    stats = engine.get_statistics()
    print(f"\n--- 最终统计 ---")
    print(f"  总种群: {stats['genome_count']}")
    print(f"  平均IQ: {stats['avg_iq']}")
    print(f"  最高IQ: {stats['max_iq']}")
    print(f"  平均复杂度: {stats['avg_complexity']}")
    print(f"  最高复杂度: L{stats['max_complexity']}")
    print(f"  总代数: {stats['total_generations']}")
    print(f"  知识池: {stats['knowledge_count']}")

    # 知识传承测试
    print(f"\n--- 知识传承测试 ---")
    engine.create_knowledge("agent_001", "resource", "forest_has_food", 1, 0.8)
    engine.create_knowledge("agent_002", "danger", "desert_is_deadly", 2, 0.9)
    engine.create_knowledge("agent_003", "social", "diplomacy_works", 3, 0.7)
    knowledge = engine.get_inheritable_knowledge(4)
    print(f"  Gen 4可继承知识: {len(knowledge)} 条")
    for k in knowledge:
        print(f"    [{k['knowledge_type']}] {k['content']} (utility={k['utility_score']})")

    engine.close()
    print("\n✅ 进化系统冒烟测试通过")
