"""
Memory manager: unified API (mem0-style) for the entire memory system.

Provides a single entry point for all memory operations:
- add: store new memory with automatic type detection and emotion tagging
- search: hybrid retrieval across all memory types
- update: modify existing memory
- delete: remove memory
- consolidate: strengthen important memories
- evolve: run decay cycle
- get_stats: system overview

This is the primary interface that agents and orchestrators should use.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import MemoryItem, MemoryType
from .config import MemoryConfig
from .cross_city_memory import CrossCityMemory
from .emotion_tagger import EmotionTagger, EmotionalMemory
from .episodic import EpisodicMemory
from .evolution import EvolutionEngine
from .graph import KnowledgeGraph
from .procedural import ProceduralMemory
from .reliability import ReliabilityScanner
from .retrieval import HybridRetriever
from .semantic import SemanticMemory
from .store import MemoryStore


class MemoryManager:
    def __init__(
        self,
        config: MemoryConfig | None = None,
        db_path: str | Path | None = None,
    ):
        self.config = config or MemoryConfig()
        if db_path:
            self.config.db_path = db_path
        self.store = MemoryStore(self.config)
        self.episodic = EpisodicMemory(self.store)
        self.semantic = SemanticMemory(self.store)
        self.procedural = ProceduralMemory(self.store)
        self.tagger = EmotionTagger()
        self.emotional = EmotionalMemory(self.store, self.tagger)
        self.graph = KnowledgeGraph(self.store)
        self.cross_city = CrossCityMemory(self.store)
        self.evolution = EvolutionEngine(self.store, self.config)
        self.retriever = HybridRetriever(self.store, self.config)
        self.reliability = ReliabilityScanner(self.store, self.config.reliability_threshold)

    def add(
        self,
        content: str,
        agent_id: str,
        memory_type: MemoryType | str | None = None,
        tags: list[str] | None = None,
        entities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        emotion: str | None = None,
        source: str | None = None,
    ) -> dict[str, Any]:
        if memory_type is None:
            memory_type = self._infer_type(content)
        elif isinstance(memory_type, str):
            memory_type = MemoryType(memory_type)

        auto_emotion = None
        auto_intensity = 0.0
        if memory_type == MemoryType.EMOTIONAL or emotion is None:
            tag_result = self.tagger.tag(content)
            auto_emotion = tag_result["primary_emotion"]
            auto_intensity = tag_result["intensity"]

        item = MemoryItem(
            content=content,
            memory_type=memory_type,
            agent_id=agent_id,
            tags=tags or [],
            entities=entities or [],
            metadata=metadata or {},
            emotion=emotion or auto_emotion,
            emotion_intensity=auto_intensity,
            source=source,
        )
        self.store.insert(item)
        return item.to_dict()

    def search(
        self,
        query: str,
        agent_id: str | None = None,
        memory_type: MemoryType | str | None = None,
        tags: list[str] | None = None,
        entities: list[str] | None = None,
        limit: int | None = None,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        mtype = None
        if memory_type:
            mtype = MemoryType(memory_type) if isinstance(memory_type, str) else memory_type
        return self.retriever.search(
            query=query,
            agent_id=agent_id,
            memory_type=mtype,
            tags=tags,
            entities=entities,
            limit=limit,
            min_score=min_score,
        )

    def get(self, memory_id: str) -> dict[str, Any] | None:
        item = self.store.get(memory_id)
        return item.to_dict() if item else None

    def update(
        self,
        memory_id: str,
        content: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        relevance_score: float | None = None,
    ) -> dict[str, Any] | None:
        item = self.store.get(memory_id)
        if not item:
            return None
        if content is not None:
            item.content = content
        if tags is not None:
            item.tags = tags
        if metadata is not None:
            item.metadata = {**item.metadata, **metadata}
        if relevance_score is not None:
            item.relevance_score = relevance_score
        item.version += 1
        self.store.update(item)
        return item.to_dict()

    def delete(self, memory_id: str) -> bool:
        return self.store.delete(memory_id)

    def consolidate(self, agent_id: str, memory_id: str) -> dict[str, Any] | None:
        item = self.evolution.consolidate(agent_id, memory_id)
        return item.to_dict() if item else None

    def evolve(self, agent_id: str) -> dict[str, Any]:
        return self.evolution.evolve_agent(agent_id)

    def relate(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        weight: float = 1.0,
    ) -> bool:
        return self.graph.connect(source_id, target_id, relationship, weight)

    def get_related(
        self,
        memory_id: str,
        agent_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        return self.retriever.search_related(memory_id, agent_id, limit)

    def get_stats(self, agent_id: str) -> dict[str, Any]:
        return {
            "agent_id": agent_id,
            "episodic_count": self.episodic.count(agent_id),
            "semantic_count": self.semantic.count(agent_id),
            "procedural_count": self.procedural.count(agent_id),
            "emotional_count": self.emotional.count(agent_id),
            "evolution": self.evolution.get_evolution_stats(agent_id),
            "graph": self.graph.get_stats(agent_id),
        }

    def get_by_agent(
        self,
        agent_id: str,
        memory_type: MemoryType | str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        mtype = None
        if memory_type:
            mtype = MemoryType(memory_type) if isinstance(memory_type, str) else memory_type
        items = self.store.get_by_agent(agent_id, mtype, limit=limit)
        return [i.to_dict() for i in items]

    def _infer_type(self, content: str) -> MemoryType:
        content_lower = content.lower()
        if any(kw in content_lower for kw in ["步骤", "流程", "如何", "方法", "skill", "how to", "procedure"]):
            return MemoryType.PROCEDURAL
        if any(kw in content_lower for kw in ["感到", "觉得", "情绪", "开心", "悲伤", "愤怒", "feel", "emotion", "happy", "sad"]):
            return MemoryType.EMOTIONAL
        if any(kw in content_lower for kw in ["事实", "数据", "知识", "定理", "fact", "data", "know"]):
            return MemoryType.SEMANTIC
        return MemoryType.EPISODIC

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> MemoryManager:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
