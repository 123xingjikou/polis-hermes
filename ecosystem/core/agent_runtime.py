# ecosystem/core/agent_runtime.py
"""
Agent 运行时 - 管理 Agent 认知状态

设计理念：
- 复用 EvolutionEngine 的基因组作为认知状态源
- 提供 Agent 状态查询和更新接口
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger("polis.agent_runtime")

class AgentRuntime:
    """
    Agent 运行时
    
    管理 Agent 的认知状态和执行环境
    """
    
    def __init__(self, data_dir: str = None):
        import os
        self.data_dir = data_dir or os.environ.get(
            "CITY_STATE_DATA_DIR",
            r"C:\Users\dfhai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a45044b9f3d6718577ed1f8\city_state_data\ecosystem"
        )
        self._evolution_adapter = None
    
    def _get_evolution(self):
        """延迟初始化进化适配器"""
        if self._evolution_adapter is None:
            from ecosystem.core.evolution_engine import EvolutionEngineAdapter
            self._evolution_adapter = EvolutionEngineAdapter(self.data_dir)
        return self._evolution_adapter
    
    def get_agent_state(self, agent_id: str) -> Dict:
        """
        获取 Agent 认知状态
        
        Returns:
            包含 IQ、复杂度、学习率等认知指标的字典
        """
        evo = self._get_evolution()
        engine = evo._get_engine()
        genome = engine.db.get_genome(agent_id)
        
        if genome:
            return {
                "agent_id": genome.agent_id,
                "iq_score": genome.iq_score,
                "complexity_level": genome.complexity_level,
                "generation": genome.generation,
                "learning_rate": genome.learning_rate,
                "memory_capacity": genome.memory_capacity,
                "planning_depth": genome.planning_depth,
                "meta_learning": genome.meta_learning,
                "social_cognition": genome.social_cognition,
                "creativity": genome.creativity,
                "abstract_reasoning": genome.abstract_reasoning,
                "emotional_intelligence": genome.emotional_intelligence,
                "species": genome.classify_species() if hasattr(genome, 'classify_species') else "unknown",
            }
        
        return {"agent_id": agent_id, "error": "not_found"}
    
    def create_agent(self, agent_id: str, generation: int = 0) -> Dict:
        """创建新 Agent"""
        evo = self._get_evolution()
        return evo.create_genome(agent_id, generation)
    
    def list_agents(self, limit: int = 100) -> list:
        """列出所有 Agent"""
        evo = self._get_evolution()
        chromosomes = evo.get_chromosomes(limit)
        return chromosomes
    
    def close(self):
        if self._evolution_adapter:
            self._evolution_adapter.close()
            self._evolution_adapter = None