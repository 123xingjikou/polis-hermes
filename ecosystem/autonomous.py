"""
⚡ 城邦生态 - Agent 自驱动系统 (Autonomous Drive System)
======================================================

解决Agent没有任务时"死掉"的问题，实现真正的自驱动行为。

借鉴GitHub主流框架的核心模式：
- 内在动机系统（好奇心、成就感、社交需求）
- 状态机驱动的行为选择
- 目标自动生成器
- 反思与学习机制
- 环境感知与主动行动

设计原则：
- 不修改 polis_v3.py 核心代码
- 通过互锁协议集成
- 每个Agent根据自身基因特性选择不同行为
- 与环境/时间/事件系统深度联动
"""

import sqlite3
import time
import random
import math
import json
import logging
import os
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable, Any
from enum import Enum
from collections import defaultdict

from .environment import EnvironmentSystem, ResourceType, Region, Season
from .temporal import TemporalSystem, TimeOfDay

logger = logging.getLogger('polis.autonomous')


# ============================================================
# 🎯 内在动机类型
# ============================================================

class MotivationType(Enum):
    """内在动机类型"""
    CURIOSITY = "curiosity"        # 好奇心驱动（探索未知）
    AMBITION = "ambition"          # 野心驱动（追求地位）
    SOCIAL = "social"              # 社交需求（结交朋友）
    LEARNING = "learning"          # 学习驱动（提升技能）
    COMFORT = "comfort"            # 舒适驱动（恢复状态）
    WEALTH = "wealth"              # 财富驱动（积累资源）
    CREATION = "creation"          # 创造驱动（生产物品）
    ADVENTURE = "adventure"        # 冒险驱动（探索区域）


class ActionType(Enum):
    """自驱动行动类型"""
    EXPLORE = "explore"            # 探索新区域
    GATHER_RESOURCES = "gather_resources"  # 采集资源
    LEARN_SKILL = "learn_skill"    # 学习技能
    SOCIALIZE = "socialize"        # 社交互动
    REST = "rest"                  # 休息恢复
    TRADE = "trade"                # 交易
    CREATE = "create"              # 创造物品
    INVESTIGATE = "investigate"    # 调查研究
    TEACH = "teach"                # 教学分享
    INNOVATE = "innovate"          # 创新


# ============================================================
# 📦 数据类
# ============================================================

@dataclass
class AgentMotivation:
    """Agent动机状态"""
    agent_id: str
    motivation_levels: Dict[str, float] = field(default_factory=lambda: {
        'curiosity': 0.5,
        'ambition': 0.5,
        'social': 0.5,
        'learning': 0.5,
        'comfort': 0.5,
        'wealth': 0.5,
        'creation': 0.5,
        'adventure': 0.5,
    })
    last_action_time: float = 0.0
    consecutive_idle_ticks: int = 0
    action_history: List[Dict] = field(default_factory=list)
    motivation_decay_rate: float = 0.02


@dataclass
class AutonomousAction:
    """自驱动行动"""
    action_id: str
    agent_id: str
    action_type: str
    motivation_type: str
    motivation_score: float
    target_region: Optional[str] = None
    target_agent: Optional[str] = None
    target_resource: Optional[str] = None
    skill_name: Optional[str] = None
    priority: float = 0.5
    duration_seconds: float = 5.0
    started_at: float = field(default_factory=time.time)
    completed: bool = False
    success: Optional[bool] = None


# ============================================================
# 🗄️ 数据库层
# ============================================================

class AutonomousDB:
    """自驱动系统数据库"""

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
        logger.info(f"AutonomousDB initialized: {self.db_path}")

    def _create_tables(self):
        cur = self._conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS motivation (
                agent_id TEXT PRIMARY KEY,
                motivation_levels TEXT NOT NULL,
                last_action_time REAL DEFAULT 0,
                consecutive_idle_ticks INTEGER DEFAULT 0,
                motivation_decay_rate REAL DEFAULT 0.02
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS action_log (
                action_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                motivation_type TEXT NOT NULL,
                motivation_score REAL NOT NULL,
                target_region TEXT DEFAULT '',
                target_agent TEXT DEFAULT '',
                target_resource TEXT DEFAULT '',
                skill_name TEXT DEFAULT '',
                priority REAL DEFAULT 0.5,
                duration_seconds REAL DEFAULT 5.0,
                started_at REAL NOT NULL,
                completed INTEGER DEFAULT 0,
                success INTEGER DEFAULT -1
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_action_agent_ts
                ON action_log(agent_id, started_at DESC)
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

    def upsert_motivation(self, mot: AgentMotivation):
        cur = self._conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO motivation
                (agent_id, motivation_levels, last_action_time,
                 consecutive_idle_ticks, motivation_decay_rate)
            VALUES (?, ?, ?, ?, ?)
        """, (mot.agent_id, json.dumps(mot.motivation_levels),
              mot.last_action_time, mot.consecutive_idle_ticks,
              mot.motivation_decay_rate))
        self._conn.commit()

    def get_motivation(self, agent_id: str) -> Optional[AgentMotivation]:
        cur = self._conn.cursor()
        row = cur.execute(
            "SELECT agent_id, motivation_levels, last_action_time, "
            "consecutive_idle_ticks, motivation_decay_rate "
            "FROM motivation WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        if not row:
            return None
        try:
            levels = json.loads(row[1])
        except json.JSONDecodeError:
            levels = {}
        return AgentMotivation(
            agent_id=row[0],
            motivation_levels=levels,
            last_action_time=row[2],
            consecutive_idle_ticks=row[3],
            motivation_decay_rate=row[4],
        )

    def insert_action(self, action: AutonomousAction):
        cur = self._conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO action_log
                (action_id, agent_id, action_type, motivation_type, motivation_score,
                 target_region, target_agent, target_resource, skill_name,
                 priority, duration_seconds, started_at, completed, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (action.action_id, action.agent_id, action.action_type,
              action.motivation_type, action.motivation_score,
              action.target_region or '', action.target_agent or '',
              action.target_resource or '', action.skill_name or '',
              action.priority, action.duration_seconds, action.started_at,
              1 if action.completed else 0,
              -1 if action.success is None else (1 if action.success else 0)))
        self._conn.commit()

    def list_agent_actions(self, agent_id: str, limit: int = 20) -> List[AutonomousAction]:
        cur = self._conn.cursor()
        rows = cur.execute("""
            SELECT action_id, agent_id, action_type, motivation_type, motivation_score,
                   target_region, target_agent, target_resource, skill_name,
                   priority, duration_seconds, started_at, completed, success
            FROM action_log WHERE agent_id = ? ORDER BY started_at DESC LIMIT ?
        """, (agent_id, limit)).fetchall()
        return [AutonomousAction(
            action_id=r[0], agent_id=r[1], action_type=r[2],
            motivation_type=r[3], motivation_score=r[4],
            target_region=r[5] or None, target_agent=r[6] or None,
            target_resource=r[7] or None, skill_name=r[8] or None,
            priority=r[9], duration_seconds=r[10], started_at=r[11],
            completed=bool(r[12]),
            success=None if r[13] == -1 else bool(r[13])
        ) for r in rows]

    def count_motivations(self) -> int:
        """统计动机记录数量"""
        cur = self._conn.cursor()
        row = cur.execute("SELECT COUNT(*) FROM motivation").fetchone()
        return row[0] if row else 0


# ============================================================
# ⚡ 自驱动核心系统
# ============================================================

class AutonomousDriveSystem:
    """
    Agent 自驱动系统 - 让Agent在没有外部任务时也能主动行动
    
    核心机制：
    1. 内在动机系统 - 根据基因特性动态调整动机强度
    2. 行为选择器 - 基于动机和环境状态选择行动
    3. 目标生成器 - 自动生成子目标和任务
    4. 反思机制 - 空闲时进行自我评估和学习
    5. 环境感知 - 根据资源、时间、事件主动响应
    """

    # 动机与行动的映射
    MOTIVATION_ACTION_MAP = {
        MotivationType.CURIOSITY: [ActionType.EXPLORE, ActionType.INVESTIGATE],
        MotivationType.AMBITION: [ActionType.INNOVATE, ActionType.TEACH],
        MotivationType.SOCIAL: [ActionType.SOCIALIZE, ActionType.TRADE],
        MotivationType.LEARNING: [ActionType.LEARN_SKILL, ActionType.INVESTIGATE],
        MotivationType.COMFORT: [ActionType.REST],
        MotivationType.WEALTH: [ActionType.GATHER_RESOURCES, ActionType.TRADE],
        MotivationType.CREATION: [ActionType.CREATE, ActionType.INNOVATE],
        MotivationType.ADVENTURE: [ActionType.EXPLORE, ActionType.INVESTIGATE],
    }

    # 行动消耗（能量/时间）
    ACTION_COST = {
        ActionType.EXPLORE: {'energy': 15.0, 'duration': 10.0},
        ActionType.GATHER_RESOURCES: {'energy': 20.0, 'duration': 8.0},
        ActionType.LEARN_SKILL: {'energy': 10.0, 'duration': 15.0},
        ActionType.SOCIALIZE: {'energy': 5.0, 'duration': 5.0},
        ActionType.REST: {'energy': -20.0, 'duration': 10.0},
        ActionType.TRADE: {'energy': 8.0, 'duration': 6.0},
        ActionType.CREATE: {'energy': 25.0, 'duration': 12.0},
        ActionType.INVESTIGATE: {'energy': 12.0, 'duration': 10.0},
        ActionType.TEACH: {'energy': 10.0, 'duration': 8.0},
        ActionType.INNOVATE: {'energy': 30.0, 'duration': 15.0},
    }

    def __init__(self, db: AutonomousDB,
                 environment: EnvironmentSystem = None,
                 temporal: TemporalSystem = None):
        self.db = db
        self.environment = environment
        self.temporal = temporal
        self._interlock_callbacks: List[callable] = []
        self._agent_genomes: Dict[str, Dict] = {}
        logger.info("AutonomousDriveSystem initialized")

    def register_interlock(self, callback: callable):
        self._interlock_callbacks.append(callback)

    def set_environment(self, env):
        self.environment = env

    def set_temporal(self, tmp):
        self.temporal = tmp

    def register_agent_genome(self, agent_id: str, genome: Dict):
        """注册Agent基因（用于动机计算）"""
        self._agent_genomes[agent_id] = genome

    # ============================================================
    # 核心方法：驱动单个Agent
    # ============================================================

    def drive_agent(self, agent_id: str, agent_state: Dict) -> Optional[AutonomousAction]:
        """
        驱动单个Agent行动
        
        agent_state 应该包含：
        - energy: 当前能量
        - health: 当前健康
        - mood: 当前心情
        - state: 当前状态（字符串）
        - role: 角色
        - skills: 技能字典
        """
        # 1. 获取/初始化动机状态
        motivation = self._get_or_init_motivation(agent_id)
        
        # 2. 更新动机（基于基因和环境）
        self._update_motivation(agent_id, motivation, agent_state)
        
        # 3. 如果没有任务且状态允许，选择行动
        current_state = agent_state.get('state', 'sleeping')
        if current_state in ['sleeping', 'resting']:
            if self._should_wake_up(agent_state):
                action = self._select_action(agent_id, motivation, agent_state)
            else:
                return None
        elif current_state in ['planning', 'idle', '']:
            action = self._select_action(agent_id, motivation, agent_state)
        else:
            # 已有任务，不干扰
            return None
        
        if action:
            # 执行行动
            result = self._execute_action(action, agent_state)
            action.completed = True
            action.success = result['success']
            self.db.insert_action(action)
            motivation.consecutive_idle_ticks = 0
            motivation.last_action_time = time.time()
            self.db.upsert_motivation(motivation)
            
            # 互锁通知
            self._notify("agent_action", {
                "agent_id": agent_id,
                "action_type": action.action_type,
                "motivation_type": action.motivation_type,
                "success": result['success'],
                "result": result,
            })
            return action
        
        # 没有选择行动，增加空闲计数
        motivation.consecutive_idle_ticks += 1
        self.db.upsert_motivation(motivation)
        return None

    def _get_or_init_motivation(self, agent_id: str) -> AgentMotivation:
        """获取或初始化动机状态"""
        mot = self.db.get_motivation(agent_id)
        if not mot:
            # 根据基因初始化动机
            genome = self._agent_genomes.get(agent_id, {})
            mot = AgentMotivation(agent_id=agent_id)
            # 基因影响初始动机
            mot.motivation_levels['curiosity'] = genome.get('curiosity', 0.5)
            mot.motivation_levels['ambition'] = genome.get('ambition', 0.5)
            mot.motivation_levels['social'] = genome.get('sociability', 0.5)
            mot.motivation_levels['learning'] = genome.get('curiosity', 0.5)
            mot.motivation_levels['adventure'] = genome.get('risk_tolerance', 0.5)
            self.db.upsert_motivation(mot)
        return mot

    def _update_motivation(self, agent_id: str, mot: AgentMotivation, agent_state: Dict):
        """
        更新动机强度
        
        影响因素：
        - 基因特性（基础）
        - 能量/健康状态（舒适动机）
        - 时间/时段（社交动机）
        - 环境资源（财富动机）
        - 空闲时间（好奇心）
        """
        genome = self._agent_genomes.get(agent_id, {})
        
        # 1. 基础动机（由基因决定）
        mot.motivation_levels['curiosity'] = max(0.1, min(1.0,
            mot.motivation_levels['curiosity'] + (genome.get('curiosity', 0.5) - 0.5) * 0.05))
        mot.motivation_levels['ambition'] = max(0.1, min(1.0,
            mot.motivation_levels['ambition'] + (genome.get('ambition', 0.5) - 0.5) * 0.05))
        mot.motivation_levels['social'] = max(0.1, min(1.0,
            mot.motivation_levels['social'] + (genome.get('sociability', 0.5) - 0.5) * 0.05))
        
        # 2. 能量低 → 舒适动机上升
        energy_ratio = agent_state.get('energy', 50) / 100.0
        if energy_ratio < 0.3:
            mot.motivation_levels['comfort'] = min(1.0, mot.motivation_levels['comfort'] + 0.1)
        elif energy_ratio > 0.8:
            mot.motivation_levels['comfort'] = max(0.1, mot.motivation_levels['comfort'] - 0.05)
        
        # 3. 健康低 → 舒适动机上升
        health_ratio = agent_state.get('health', 100) / 100.0
        if health_ratio < 0.5:
            mot.motivation_levels['comfort'] = min(1.0, mot.motivation_levels['comfort'] + 0.15)
        
        # 4. 空闲时间长 → 好奇心上升
        if mot.consecutive_idle_ticks > 5:
            mot.motivation_levels['curiosity'] = min(1.0,
                mot.motivation_levels['curiosity'] + 0.05 * mot.consecutive_idle_ticks / 10)
        
        # 5. 时间影响（早晨学习，傍晚社交）
        if self.temporal:
            tod = self.temporal.get_time_of_day()
            if tod == TimeOfDay.MORNING:
                mot.motivation_levels['learning'] = min(1.0,
                    mot.motivation_levels['learning'] + 0.1)
            elif tod == TimeOfDay.DUSK:
                mot.motivation_levels['social'] = min(1.0,
                    mot.motivation_levels['social'] + 0.1)
            elif tod == TimeOfDay.NIGHT:
                mot.motivation_levels['comfort'] = min(1.0,
                    mot.motivation_levels['comfort'] + 0.15)
        
        # 6. 环境资源稀缺 → 财富动机上升
        if self.environment:
            entropy = self.environment.calculate_entropy()
            if entropy > 0.5:
                mot.motivation_levels['wealth'] = min(1.0,
                    mot.motivation_levels['wealth'] + 0.05)
        
        # 7. 动机衰减（防止某个动机无限增长）
        for key in mot.motivation_levels:
            mot.motivation_levels[key] = max(0.1, min(1.0,
                mot.motivation_levels[key] - mot.motivation_decay_rate))

    def _should_wake_up(self, agent_state: Dict) -> bool:
        """判断是否应该唤醒"""
        energy = agent_state.get('energy', 0)
        return energy > 30

    def _select_action(self, agent_id: str, mot: AgentMotivation,
                       agent_state: Dict) -> Optional[AutonomousAction]:
        """
        选择行动 - 核心算法
        
        基于：动机强度 + 状态条件 + 环境信息
        """
        energy = agent_state.get('energy', 50)
        health = agent_state.get('health', 100)
        role = agent_state.get('role', '')
        
        # 生成候选行动及其得分
        candidates = []
        
        for mot_type, actions in self.MOTIVATION_ACTION_MAP.items():
            mot_score = mot.motivation_levels.get(mot_type.value, 0.5)
            if mot_score < 0.2:
                continue
            
            for action_type in actions:
                # 检查能量是否足够
                cost = self.ACTION_COST.get(action_type, {'energy': 10.0})
                if action_type != ActionType.REST and energy < cost['energy'] + 5:
                    continue
                
                # 检查健康是否允许
                if health < 20 and action_type not in [ActionType.REST, ActionType.TEACH]:
                    continue
                
                # 角色偏好
                role_bonus = self._get_role_bonus(role, action_type)
                
                # 最终得分
                score = mot_score * (0.8 + role_bonus * 0.2)
                
                candidates.append({
                    'action_type': action_type,
                    'motivation_type': mot_type,
                    'score': score,
                    'motivation_score': mot_score,
                    'energy_cost': cost['energy'],
                    'duration': cost['duration'],
                })
        
        if not candidates:
            return None
        
        # 选择得分最高的
        candidates.sort(key=lambda x: -x['score'])
        best = candidates[0]
        
        # 构建行动对象
        action = AutonomousAction(
            action_id=f"act_{int(time.time()*1000)}_{random.randint(1000,9999)}",
            agent_id=agent_id,
            action_type=best['action_type'].value,
            motivation_type=best['motivation_type'].value,
            motivation_score=best['motivation_score'],
            priority=best['score'],
            duration_seconds=best['duration'],
        )
        
        # 设置具体目标
        self._set_action_target(action, agent_id, agent_state)
        
        return action

    def _get_role_bonus(self, role: str, action_type: ActionType) -> float:
        """角色对行动的偏好加成"""
        role_bonuses = {
            'SCHOLAR': {
                ActionType.LEARN_SKILL: 1.3,
                ActionType.INVESTIGATE: 1.3,
                ActionType.TEACH: 1.2,
            },
            'MERCHANT': {
                ActionType.TRADE: 1.3,
                ActionType.GATHER_RESOURCES: 1.2,
                ActionType.INNOVATE: 1.1,
            },
            'ARTISAN': {
                ActionType.CREATE: 1.3,
                ActionType.INNOVATE: 1.2,
                ActionType.LEARN_SKILL: 1.1,
            },
            'EXPLORER': {
                ActionType.EXPLORE: 1.3,
                ActionType.INVESTIGATE: 1.2,
            },
            'DIPLOMAT': {
                ActionType.SOCIALIZE: 1.3,
                ActionType.TRADE: 1.2,
                ActionType.TEACH: 1.1,
            },
            'INNOVATOR': {
                ActionType.INNOVATE: 1.3,
                ActionType.LEARN_SKILL: 1.2,
                ActionType.INVESTIGATE: 1.2,
            },
            'GUARDIAN': {
                ActionType.SOCIALIZE: 1.2,
                ActionType.INVESTIGATE: 1.1,
                ActionType.TEACH: 1.1,
            },
            'HEALER': {
                ActionType.TEACH: 1.3,
                ActionType.LEARN_SKILL: 1.2,
                ActionType.SOCIALIZE: 1.1,
            },
        }
        role_key = role.upper() if role else ''
        return role_bonuses.get(role_key, {}).get(action_type, 1.0)

    def _set_action_target(self, action: AutonomousAction,
                          agent_id: str, agent_state: Dict):
        """设置行动的具体目标"""
        action_type = ActionType(action.action_type)
        
        if action_type == ActionType.EXPLORE and self.environment:
            regions = self.environment.list_regions()
            if regions:
                action.target_region = random.choice(regions).region_id
        
        elif action_type == ActionType.GATHER_RESOURCES and self.environment:
            regions = self.environment.list_regions()
            if regions:
                region = random.choice(regions)
                action.target_region = region.region_id
                resources = self.environment.get_all_resources(region.region_id)
                if resources:
                    # 优先采集稀缺资源
                    sorted_resources = sorted(resources.items(), key=lambda x: x[1])
                    action.target_resource = sorted_resources[0][0]
        
        elif action_type == ActionType.LEARN_SKILL:
            skills = agent_state.get('skills', {})
            if skills:
                # 优先学习等级最低的技能
                weakest_skill = min(skills.items(), key=lambda x: x[1].get('level', 0))
                action.skill_name = weakest_skill[0]
        
        elif action_type == ActionType.SOCIALIZE:
            # 需要从社会系统获取其他Agent列表（这里留空，由调用方填充）
            pass
        
        elif action_type == ActionType.TRADE:
            if self.environment:
                regions = self.environment.list_regions()
                if regions:
                    action.target_region = random.choice(regions).region_id

    def _execute_action(self, action: AutonomousAction,
                       agent_state: Dict) -> Dict:
        """
        执行行动 - 返回结果
        
        注意：这里是模拟执行，实际执行需要与环境/社会系统交互
        """
        action_type = ActionType(action.action_type)
        
        # 能量变化
        cost = self.ACTION_COST.get(action_type, {'energy': 10.0})
        energy_change = -cost['energy'] if action_type != ActionType.REST else abs(cost['energy'])
        
        # 成功概率
        success_prob = min(0.95, max(0.5, action.motivation_score))
        success = random.random() < success_prob
        
        result = {
            'success': success,
            'action_type': action.action_type,
            'energy_change': energy_change,
            'duration': action.duration_seconds,
        }
        
        if success:
            # 根据行动类型添加额外效果
            if action_type == ActionType.GATHER_RESOURCES:
                result['resources_gathered'] = random.uniform(5, 20)
            elif action_type == ActionType.LEARN_SKILL:
                result['skill_exp'] = random.uniform(10, 30)
            elif action_type == ActionType.SOCIALIZE:
                result['social_bonus'] = random.uniform(0.01, 0.05)
            elif action_type == ActionType.TRADE:
                result['wealth_change'] = random.uniform(-10, 30)
            elif action_type == ActionType.INNOVATE:
                result['innovation_score'] = random.uniform(0.1, 0.5)
        
        return result

    # ============================================================
    # 批量驱动方法
    # ============================================================

    def get_motivation_count(self) -> int:
        """获取有动机记录的 Agent 数量"""
        return self.db.count_motivations()

    def drive_all(self, agents_state: Dict[str, Dict]) -> Dict[str, Optional[AutonomousAction]]:
        """驱动所有Agent"""
        results = {}
        for agent_id, state in agents_state.items():
            action = self.drive_agent(agent_id, state)
            results[agent_id] = action
        return results

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'registered_genomes': len(self._agent_genomes),
            'interlock_callbacks': len(self._interlock_callbacks),
        }

    def _notify(self, event_type: str, data: dict):
        for cb in self._interlock_callbacks:
            try:
                cb("autonomous", event_type, data)
            except Exception as e:
                logger.warning(f"Autonomous interlock callback failed: {e}")


# ============================================================
# 🚀 工厂函数
# ============================================================

def create_default_autonomous(data_dir: str = None,
                              environment: EnvironmentSystem = None,
                              temporal: TemporalSystem = None) -> AutonomousDriveSystem:
    if data_dir is None:
        data_dir = os.environ.get(
            "CITY_STATE_DATA_DIR",
            r"C:\Users\dfhai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a45044b9f3d6718577ed1f8\city_state_data\ecosystem"
        )
    db_path = os.path.join(data_dir, "state", "autonomous.db")
    db = AutonomousDB(db_path)
    sys = AutonomousDriveSystem(db, environment, temporal)
    return sys


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    
    # 冒烟测试
    from .environment import create_default_environment
    from .temporal import create_default_temporal
    
    env = create_default_environment()
    tmp = create_default_temporal()
    ads = create_default_autonomous(environment=env, temporal=tmp)
    
    # 注册几个测试Agent
    ads.register_agent_genome("agent_001", {
        'curiosity': 0.8, 'ambition': 0.6, 'sociability': 0.5, 'risk_tolerance': 0.7
    })
    ads.register_agent_genome("agent_002", {
        'curiosity': 0.4, 'ambition': 0.8, 'sociability': 0.7, 'risk_tolerance': 0.3
    })
    ads.register_agent_genome("agent_003", {
        'curiosity': 0.5, 'ambition': 0.3, 'sociability': 0.9, 'risk_tolerance': 0.4
    })
    
    # 模拟驱动
    print("\n=== 自驱动系统冒烟测试 ===")
    for i in range(5):
        print(f"\n--- Tick {i+1} ---")
        agents_state = {
            "agent_001": {"energy": 80, "health": 90, "mood": 70, "state": "idle", "role": "EXPLORER"},
            "agent_002": {"energy": 60, "health": 85, "mood": 60, "state": "idle", "role": "SCHOLAR"},
            "agent_003": {"energy": 70, "health": 95, "mood": 80, "state": "idle", "role": "DIPLOMAT"},
        }
        results = ads.drive_all(agents_state)
        for aid, action in results.items():
            if action:
                print(f"  {aid}: {action.action_type} (动机:{action.motivation_type}, 得分:{action.priority:.2f})")
            else:
                print(f"  {aid}: 无行动")
    
    ads.db.close()
    env.db.close()
    tmp.db.close()
    print("\n✅ 冒烟测试通过")
