"""
Hybrid retrieval: semantic + keyword + temporal + entity fusion.

Combines multiple retrieval signals using a weighted scoring fusion:
- Full-text keyword matching (FTS5 BM25)
- Tag-based filtering
- Entity-relation graph traversal
- Temporal recency weighting
- Effective score ranking (relevance * strength * decay * reliability)

Inspired by mem0's hybrid retrieval with entity linking and Zep's temporal
decay weighting.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .base import MemoryItem, MemoryType
from .config import MemoryConfig
from .store import MemoryStore


class HybridRetriever:
    WEIGHT_FULLTEXT = 0.35
    WEIGHT_TAG = 0.20
    WEIGHT_ENTITY = 0.25
    WEIGHT_TEMPORAL = 0.10
    WEIGHT_SCORE = 0.10

    def __init__(self, store: MemoryStore, config: MemoryConfig | None = None):
        self.store = store
        self.config = config or MemoryConfig()

    def search(
        self,
        query: str,
        agent_id: str | None = None,
        memory_type: MemoryType | None = None,
        tags: list[str] | None = None,
        entities: list[str] | None = None,
        limit: int | None = None,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        target_limit = limit or self.config.default_retrieval_limit
        candidates: dict[str, dict[str, Any]] = {}

        fts_results = self.store.search_fulltext(query, agent_id, limit=target_limit * 3)
        for rank, item in enumerate(fts_results):
            if memory_type and item.memory_type != memory_type:
                continue
            score = self.WEIGHT_FULLTEXT * (1.0 / (1.0 + rank))
            candidates[item.memory_id] = {
                "item": item,
                "score": score,
                "signals": ["fulltext"],
            }

        if tags:
            tag_results = self.store.search_by_tags(tags, agent_id, limit=target_limit * 3)
            for item in tag_results:
                if memory_type and item.memory_type != memory_type:
                    continue
                if item.memory_id in candidates:
                    candidates[item.memory_id]["score"] += self.WEIGHT_TAG
                    candidates[item.memory_id]["signals"].append("tag")
                else:
                    candidates[item.memory_id] = {
                        "item": item,
                        "score": self.WEIGHT_TAG,
                        "signals": ["tag"],
                    }

        if entities:
            for entity in entities:
                entity_results = self.store.search_fulltext(entity, agent_id, limit=target_limit * 2)
                for item in entity_results:
                    if memory_type and item.memory_type != memory_type:
                        continue
                    if item.memory_id in candidates:
                        candidates[item.memory_id]["score"] += self.WEIGHT_ENTITY / len(entities)
                        if "entity" not in candidates[item.memory_id]["signals"]:
                            candidates[item.memory_id]["signals"].append("entity")
                    else:
                        candidates[item.memory_id] = {
                            "item": item,
                            "score": self.WEIGHT_ENTITY / len(entities),
                            "signals": ["entity"],
                        }

        for _mid, entry in candidates.items():
            item = entry["item"]
            temporal_score = self._temporal_weight(item)
            entry["score"] += self.WEIGHT_TEMPORAL * temporal_score
            entry["score"] += self.WEIGHT_SCORE * item.effective_score

        results = []
        for _mid, entry in candidates.items():
            item = entry["item"]
            final_score = entry["score"]
            if min_score is not None and final_score < min_score:
                continue
            results.append({
                "memory_id": item.memory_id,
                "content": item.content,
                "memory_type": item.memory_type.value,
                "agent_id": item.agent_id,
                "score": round(final_score, 4),
                "effective_score": round(item.effective_score, 4),
                "signals": entry["signals"],
                "stage": item.stage.value,
                "tags": item.tags,
                "entities": item.entities,
                "emotion": item.emotion,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:target_limit]

    def search_related(
        self,
        memory_id: str,
        agent_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        source = self.store.get(memory_id)
        if not source:
            return []

        entities = source.entities
        tags = source.tags
        query = source.content[:50]

        results = self.search(
            query=query,
            agent_id=agent_id,
            tags=tags if tags else None,
            entities=entities if entities else None,
            limit=limit + 1,
        )
        return [r for r in results if r["memory_id"] != memory_id][:limit]

    def search_by_emotion(
        self,
        emotion: str,
        agent_id: str | None = None,
        min_intensity: float = 0.0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        results = self.store.search_by_emotion(emotion, agent_id, limit=limit * 2)
        filtered = [r for r in results if r.emotion_intensity >= min_intensity]
        filtered.sort(key=lambda x: x.emotion_intensity, reverse=True)
        return [
            {
                "memory_id": r.memory_id,
                "content": r.content,
                "emotion_intensity": r.emotion_intensity,
                "effective_score": round(r.effective_score, 4),
            }
            for r in filtered[:limit]
        ]

    def _temporal_weight(self, item: MemoryItem) -> float:
        try:
            created = datetime.fromisoformat(item.created_at)
            age_hours = max(
                (datetime.now(timezone.utc) - created).total_seconds() / 3600, 0
            )
            import math
            return math.exp(-0.01 * age_hours)
        except (ValueError, TypeError):
            return 0.5
