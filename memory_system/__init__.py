"""
Memory System for Polis-Hermes
===============================

An evolutionary, super-intelligent agent memory system combining:
- Multi-type memory (Episodic, Semantic, Procedural, Emotional)
- Hybrid retrieval (semantic + keyword + temporal + entity)
- Knowledge graph relationships
- Cross-city distributed memory
- Ebbinghaus forgetting curve with reinforcement
- Reliability scoring and emotion tagging
"""

from .base import MemoryItem, MemoryPriority, MemoryStage, MemoryType
from .config import MemoryConfig, MemoryLevel
from .cross_city_memory import CrossCityMemory, CrossCityMemoryClient, CrossCityMemoryQuery
from .emotion_tagger import EmotionTagger, EmotionalMemory
from .episodic import EpisodicMemory
from .evolution import EvolutionEngine
from .graph import KnowledgeGraph
from .manager import MemoryManager
from .procedural import ProceduralMemory
from .reliability import AgentReliabilityScorer, ReliabilityScanner, ReliabilityScore
from .retrieval import HybridRetriever
from .semantic import SemanticMemory
from .store import MemoryStore

__all__ = [
    "AgentReliabilityScorer",
    "CrossCityMemory",
    "CrossCityMemoryClient",
    "CrossCityMemoryQuery",
    "EmotionTagger",
    "EmotionalMemory",
    "EpisodicMemory",
    "EvolutionEngine",
    "HybridRetriever",
    "KnowledgeGraph",
    "MemoryConfig",
    "MemoryItem",
    "MemoryLevel",
    "MemoryManager",
    "MemoryPriority",
    "MemoryStage",
    "MemoryStore",
    "MemoryType",
    "ProceduralMemory",
    "ReliabilityScanner",
    "ReliabilityScore",
    "SemanticMemory",
]

__version__ = "1.0.0"
