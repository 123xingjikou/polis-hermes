"""
Procedural memory: stores skills, behaviors, and learned procedures.

Inspired by Letta/MemGPT's "memory as code" pattern — procedural memories
are executable behavioral patterns that improve with practice.
"""

from __future__ import annotations

from .base import MemoryItem, MemoryPriority, MemoryStage, MemoryType
from .store import MemoryStore


class ProceduralMemory:
    def __init__(self, store: MemoryStore):
        self.store = store

    def learn(
        self,
        agent_id: str,
        skill_name: str,
        steps: str,
        success_rate: float = 0.5,
        source: str | None = None,
        tags: list[str] | None = None,
    ) -> MemoryItem:
        item = MemoryItem(
            content=f"[{skill_name}]\n{steps}",
            memory_type=MemoryType.PROCEDURAL,
            agent_id=agent_id,
            stage=MemoryStage.LONG_TERM,
            source=source,
            tags=tags or [skill_name],
            relevance_score=success_rate,
            priority=self._success_to_priority(success_rate),
            metadata={"skill_name": skill_name, "success_rate": success_rate, "practice_count": 0},
        )
        self.store.insert(item)
        return item

    def recall(
        self,
        agent_id: str,
        query: str | None = None,
        tags: list[str] | None = None,
        min_success_rate: float = 0.0,
        limit: int = 20,
    ) -> list[MemoryItem]:
        if query:
            results = self.store.search_fulltext(query, agent_id, limit=limit * 2)
            results = [r for r in results if r.memory_type == MemoryType.PROCEDURAL]
        elif tags:
            results = self.store.search_by_tags(tags, agent_id, limit=limit * 2)
            results = [r for r in results if r.memory_type == MemoryType.PROCEDURAL]
        else:
            results = self.store.get_by_agent(
                agent_id, MemoryType.PROCEDURAL, limit=limit * 2
            )

        filtered = [
            r for r in results
            if r.memory_type == MemoryType.PROCEDURAL
            and r.relevance_score >= min_success_rate
        ]
        filtered.sort(key=lambda x: x.effective_score, reverse=True)
        return filtered[:limit]

    def practice(
        self,
        agent_id: str,
        memory_id: str,
        success: bool,
    ) -> MemoryItem | None:
        item = self.store.get(memory_id)
        if not item or item.agent_id != agent_id:
            return None
        practice_count = item.metadata.get("practice_count", 0) + 1
        current_rate = item.relevance_score
        if success:
            new_rate = min(1.0, current_rate + 0.05)
            item.strengthen(0.1)
        else:
            new_rate = max(0.0, current_rate - 0.03)
            item.weaken(0.05)
        item.metadata["practice_count"] = practice_count
        item.metadata["success_rate"] = new_rate
        item.relevance_score = new_rate
        item.version += 1
        self.store.update(item)
        return item

    def get_skills(self, agent_id: str, limit: int = 50) -> list[MemoryItem]:
        items = self.store.get_by_agent(
            agent_id, MemoryType.PROCEDURAL, limit=limit
        )
        return sorted(items, key=lambda x: x.effective_score, reverse=True)

    def forget(self, agent_id: str, memory_id: str) -> bool:
        item = self.store.get(memory_id)
        if not item or item.agent_id != agent_id:
            return False
        item.is_valid = False
        self.store.update(item)
        return True

    def count(self, agent_id: str) -> int:
        return self.store.count_by_agent(agent_id, MemoryType.PROCEDURAL)

    @staticmethod
    def _success_to_priority(success_rate: float) -> MemoryPriority:
        if success_rate >= 0.9:
            return MemoryPriority.CRITICAL
        if success_rate >= 0.7:
            return MemoryPriority.HIGH
        if success_rate >= 0.4:
            return MemoryPriority.NORMAL
        return MemoryPriority.LOW
