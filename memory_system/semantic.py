"""
Semantic memory: stores facts, concepts, and general knowledge.
"""

from __future__ import annotations

from .base import MemoryItem, MemoryPriority, MemoryStage, MemoryType
from .store import MemoryStore


class SemanticMemory:
    def __init__(self, store: MemoryStore):
        self.store = store

    def learn(
        self,
        agent_id: str,
        fact: str,
        confidence: float = 0.8,
        source: str | None = None,
        entities: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> MemoryItem:
        item = MemoryItem(
            content=fact,
            memory_type=MemoryType.SEMANTIC,
            agent_id=agent_id,
            stage=MemoryStage.LONG_TERM,
            source=source,
            entities=entities or [],
            tags=tags or [],
            relevance_score=confidence,
            priority=self._confidence_to_priority(confidence),
        )
        self.store.insert(item)
        return item

    def recall(
        self,
        agent_id: str,
        query: str | None = None,
        entities: list[str] | None = None,
        tags: list[str] | None = None,
        min_confidence: float = 0.0,
        limit: int = 20,
    ) -> list[MemoryItem]:
        results: list[MemoryItem]
        if query:
            results = self.store.search_fulltext(query, agent_id, limit=limit * 2)
            results = [r for r in results if r.memory_type == MemoryType.SEMANTIC]
        elif tags:
            results = self.store.search_by_tags(tags, agent_id, limit=limit * 2)
            results = [r for r in results if r.memory_type == MemoryType.SEMANTIC]
        elif entities:
            all_results: list[MemoryItem] = []
            for entity in entities:
                found = self.store.search_fulltext(
                    entity, agent_id, limit=limit
                )
                all_results.extend(
                    r for r in found
                    if r.memory_type == MemoryType.SEMANTIC
                    and r not in all_results
                )
            results = all_results
        else:
            results = self.store.get_by_agent(
                agent_id, MemoryType.SEMANTIC, limit=limit * 2
            )

        filtered = [
            r for r in results
            if r.memory_type == MemoryType.SEMANTIC
            and r.relevance_score >= min_confidence
        ]
        filtered.sort(key=lambda x: x.effective_score, reverse=True)
        return filtered[:limit]

    def update_fact(
        self,
        agent_id: str,
        memory_id: str,
        new_fact: str,
        confidence: float | None = None,
    ) -> MemoryItem | None:
        item = self.store.get(memory_id)
        if not item or item.agent_id != agent_id:
            return None
        item.content = new_fact
        if confidence is not None:
            item.relevance_score = confidence
        item.version += 1
        item.priority = self._confidence_to_priority(item.relevance_score)
        self.store.update(item)
        return item

    def forget(self, agent_id: str, memory_id: str) -> bool:
        item = self.store.get(memory_id)
        if not item or item.agent_id != agent_id:
            return False
        item.is_valid = False
        self.store.update(item)
        return True

    def get_knowledge_base(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> list[MemoryItem]:
        items = self.store.get_by_agent(
            agent_id, MemoryType.SEMANTIC, limit=limit
        )
        return sorted(items, key=lambda x: x.effective_score, reverse=True)

    def extract_entities(self, agent_id: str) -> set[str]:
        items = self.store.get_by_agent(
            agent_id, MemoryType.SEMANTIC, limit=1000
        )
        entities: set[str] = set()
        for item in items:
            entities.update(item.entities)
        return entities

    def count(self, agent_id: str) -> int:
        return self.store.count_by_agent(agent_id, MemoryType.SEMANTIC)

    @staticmethod
    def _confidence_to_priority(confidence: float) -> MemoryPriority:
        if confidence >= 0.9:
            return MemoryPriority.CRITICAL
        if confidence >= 0.7:
            return MemoryPriority.HIGH
        if confidence >= 0.4:
            return MemoryPriority.NORMAL
        return MemoryPriority.LOW
