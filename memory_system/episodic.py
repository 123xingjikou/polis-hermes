"""
Episodic memory: stores specific events and experiences.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .base import MemoryItem, MemoryStage, MemoryType
from .store import MemoryStore


class EpisodicMemory:
    def __init__(self, store: MemoryStore):
        self.store = store

    def record(
        self,
        agent_id: str,
        event: str,
        context: str | None = None,
        timestamp: str | None = None,
        location: str | None = None,
        participants: list[str] | None = None,
        outcome: str | None = None,
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> MemoryItem:
        metadata: dict[str, Any] = {}
        if location:
            metadata["location"] = location
        if participants:
            metadata["participants"] = participants
        if outcome:
            metadata["outcome"] = outcome
        metadata["importance"] = importance

        full_context = context or ""
        if participants:
            full_context += f" | participants: {', '.join(participants)}"
        if outcome:
            full_context += f" | outcome: {outcome}"

        created = timestamp or datetime.now(timezone.utc).isoformat()

        item = MemoryItem(
            content=event,
            memory_type=MemoryType.EPISODIC,
            agent_id=agent_id,
            stage=MemoryStage.SHORT_TERM,
            created_at=created,
            updated_at=created,
            context=full_context,
            entities=participants or [],
            metadata=metadata,
            tags=tags or [],
            relevance_score=importance,
            priority=self._importance_to_priority(importance),
        )
        self.store.insert(item)
        return item

    def recall(
        self,
        agent_id: str,
        query: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        participants: list[str] | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        if query:
            results = self.store.search_fulltext(query, agent_id, limit=limit * 2)
            results = [r for r in results if r.memory_type == MemoryType.EPISODIC]
        elif tags:
            results = self.store.search_by_tags(tags, agent_id, limit=limit * 2)
            results = [r for r in results if r.memory_type == MemoryType.EPISODIC]
        else:
            results = self.store.get_by_agent(
                agent_id, MemoryType.EPISODIC, limit=limit * 2
            )

        filtered: list[MemoryItem] = []
        for r in results:
            if r.memory_type != MemoryType.EPISODIC:
                continue
            if start_time and r.created_at < start_time:
                continue
            if end_time and r.created_at > end_time:
                continue
            if participants:
                meta_participants = r.metadata.get("participants", [])
                if not any(p in meta_participants for p in participants):
                    continue
            filtered.append(r)

        filtered.sort(key=lambda x: x.created_at, reverse=True)
        return filtered[:limit]

    def consolidate(self, agent_id: str, memory_id: str) -> MemoryItem | None:
        item = self.store.get(memory_id)
        if not item or item.agent_id != agent_id:
            return None
        item.stage = MemoryStage.CONSOLIDATED
        item.strength = min(2.0, item.strength + 0.5)
        item.priority = MemoryStage.CONSOLIDATED  # type: ignore[assignment]
        self.store.update(item)
        return item

    def get_timeline(
        self,
        agent_id: str,
        days: int = 7,
        limit: int = 50,
    ) -> list[MemoryItem]:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=days)
        ).isoformat()
        items = self.store.get_by_agent(
            agent_id, MemoryType.EPISODIC, limit=limit
        )
        items = [i for i in items if i.created_at >= cutoff]
        items.sort(key=lambda x: x.created_at)
        return items

    def count(self, agent_id: str) -> int:
        return self.store.count_by_agent(agent_id, MemoryType.EPISODIC)

    @staticmethod
    def _importance_to_priority(importance: float):
        from .base import MemoryPriority
        if importance >= 0.8:
            return MemoryPriority.CRITICAL
        if importance >= 0.6:
            return MemoryPriority.HIGH
        if importance >= 0.3:
            return MemoryPriority.NORMAL
        return MemoryPriority.LOW
