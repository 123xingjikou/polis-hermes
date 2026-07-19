"""
Configuration for the memory system.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class MemoryLevel(str, Enum):
    AGENT = "agent"
    SESSION = "session"
    CITY = "city"
    CROSS_CITY = "cross_city"


@dataclass
class MemoryConfig:
    db_path: str | Path = "memory.db"
    fts_enabled: bool = True
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    max_memories_per_agent: int = 10000
    max_episodic_memories: int = 5000
    max_semantic_memories: int = 3000
    max_procedural_memories: int = 2000
    max_emotional_memories: int = 2000
    default_retrieval_limit: int = 20
    relevance_threshold: float = 0.6
    ebbinghaus_decay_rate: float = 0.15
    reinforcement_boost: float = 0.3
    decay_interval_hours: int = 24
    reliability_threshold: float = 0.4
    emotion_decay_hours: int = 48
    graph_max_nodes: int = 5000
    graph_max_edges: int = 20000
    sync_interval_seconds: int = 300
    auto_evolution: bool = True
    auto_reliability_scan: bool = True
    debug: bool = False

    @property
    def db_path_str(self) -> str:
        return str(self.db_path)

    def to_dict(self) -> dict:
        return {
            "db_path": str(self.db_path),
            "fts_enabled": self.fts_enabled,
            "embedding_model": self.embedding_model,
            "embedding_dimension": self.embedding_dimension,
            "max_memories_per_agent": self.max_memories_per_agent,
            "default_retrieval_limit": self.default_retrieval_limit,
            "relevance_threshold": self.relevance_threshold,
            "auto_evolution": self.auto_evolution,
            "debug": self.debug,
        }
