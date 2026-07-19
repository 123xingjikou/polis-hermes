# ecosystem/core/__init__.py
"""
Hermes 桥接核心模块

将 ecosystem 子系统适配为 Hermes 期望的接口，
解决 polis_hermes_bridge.py 中 8 个模块导入失败的问题。
"""

from ecosystem.core.memory_cascade import MemoryCascade
from ecosystem.core.evolution_engine import EvolutionEngineAdapter
from ecosystem.core.orchestrator import Orchestrator
from ecosystem.core.skill_registry import SkillRegistry
from ecosystem.core.agent_runtime import AgentRuntime
from ecosystem.core.plugins.economy import EconomicMatching
from ecosystem.core.plugins.social_graph import SocialGraph
from ecosystem.core.plugins.reputation_assigner import ReputationAssigner

__all__ = [
    'MemoryCascade',
    'EvolutionEngineAdapter',
    'Orchestrator',
    'SkillRegistry',
    'AgentRuntime',
    'EconomicMatching',
    'SocialGraph',
    'ReputationAssigner',
]