# ecosystem/core/skill_registry.py
"""
技能注册表 - 管理 Agent 可用技能

设计理念：
- 技能是可复用的能力单元
- 支持技能注册、查询、解锁
"""

import json
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("polis.skill_registry")

@dataclass
class Skill:
    """技能定义"""
    skill_id: str
    skill_name: str
    description: str
    level: int  # 1-10
    category: str  # combat, social, crafting, magic, etc.
    prerequisites: List[str]  # 前置技能
    effects: Dict  # 效果

class SkillRegistry:
    """
    技能注册表
    
    管理所有可用技能及其解锁条件
    """
    
    DEFAULT_SKILLS = [
        {"skill_id": "basic_combat", "skill_name": "基础战斗", "description": "基础战斗技能", "level": 1, "category": "combat", "prerequisites": [], "effects": {"attack_bonus": 5}},
        {"skill_id": "basic_diplomacy", "skill_name": "基础外交", "description": "基础外交技能", "level": 1, "category": "social", "prerequisites": [], "effects": {"persuasion": 10}},
        {"skill_id": "basic_crafting", "skill_name": "基础制造", "description": "基础制造技能", "level": 1, "category": "crafting", "prerequisites": [], "effects": {"crafting_speed": 1.1}},
        {"skill_id": "advanced_combat", "skill_name": "高级战斗", "description": "高级战斗技能", "level": 3, "category": "combat", "prerequisites": ["basic_combat"], "effects": {"attack_bonus": 15}},
        {"skill_id": "master_diplomacy", "skill_name": "外交大师", "description": "外交大师技能", "level": 5, "category": "social", "prerequisites": ["basic_diplomacy"], "effects": {"persuasion": 30}},
    ]
    
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._load_defaults()
    
    def _load_defaults(self):
        """加载默认技能"""
        for s in self.DEFAULT_SKILLS:
            self.register(
                skill_id=s["skill_id"],
                skill_name=s["skill_name"],
                description=s["description"],
                level=s["level"],
                category=s["category"],
                prerequisites=s.get("prerequisites", []),
                effects=s.get("effects", {})
            )
    
    def register(self, skill_id: str, skill_name: str, description: str,
                 level: int, category: str, prerequisites: List[str] = None,
                 effects: Dict = None) -> bool:
        """注册新技能"""
        if skill_id in self._skills:
            logger.warning(f"Skill already exists: {skill_id}")
            return False
        
        self._skills[skill_id] = Skill(
            skill_id=skill_id,
            skill_name=skill_name,
            description=description,
            level=level,
            category=category,
            prerequisites=prerequisites or [],
            effects=effects or {}
        )
        
        logger.info(f"Skill registered: {skill_id} ({skill_name})")
        return True
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取技能"""
        return self._skills.get(skill_id)
    
    def list_skills(self, category: str = None, min_level: int = 0) -> List[Skill]:
        """列出技能"""
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        if min_level:
            skills = [s for s in skills if s.level >= min_level]
        return skills
    
    def can_unlock(self, agent_skills: List[str], skill_id: str) -> bool:
        """检查是否可以解锁"""
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        
        # 检查前置技能
        for prereq in skill.prerequisites:
            if prereq not in agent_skills:
                return False
        
        return True