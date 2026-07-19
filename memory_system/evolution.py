"""
Evolution engine: Ebbinghaus forgetting curve with reinforcement learning.

Implements memory consolidation through:
- Ebbinghaus decay: memories weaken over time without access
- Access reinforcement: each retrieval strengthens the memory
- Stage progression: working → short_term → long_term → consolidated
- Automatic quality-based promotion and demotion

Based on the classic Ebbinghaus forgetting curve: R = e^(-t/S)
where R is retention, t is time, and S is memory strength.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from .base import MemoryItem, MemoryStage
from .config import MemoryConfig
from .store import MemoryStore


class EvolutionEngine:
    def __init__(self, store: MemoryStore, config: MemoryConfig | None = None):
        self.store = store
        self.config = config or MemoryConfig()
        self._decay_rate = self.config.ebbinghaus_decay_rate
        self._reinforcement = self.config.reinforcement_boost

    def compute_retention(self, item: MemoryItem) -> float:
        try:
            created = datetime.fromisoformat(item.created_at)
            now = datetime.now(timezone.utc)
            hours_elapsed = max((now - created).total_seconds() / 3600, 0)
        except (ValueError, TypeError):
            return item.strength

        access_boost = math.log1p(item.access_count) * self._reinforcement
        effective_strength = max(item.strength + access_boost, 0.1)
        retention = math.exp(-self._decay_rate * hours_elapsed / effective_strength)
        return max(0.0, min(1.0, retention))

    def apply_decay(self, item: MemoryItem) -> MemoryItem:
        retention = self.compute_retention(item)
        item.decay_factor = retention
        if retention < 0.1 and item.stage != MemoryStage.CONSOLIDATED:
            item.weaken(0.3)
        elif retention < 0.3:
            item.weaken(0.1)
        return item

    def reinforce(self, item: MemoryItem, amount: float | None = None) -> MemoryItem:
        boost = amount or self._reinforcement
        item.strengthen(boost)
        item.mark_accessed()
        if item.access_count >= 3 and item.stage == MemoryStage.WORKING:
            item.stage = MemoryStage.SHORT_TERM
        if item.access_count >= 7 and item.stage == MemoryStage.SHORT_TERM:
            item.stage = MemoryStage.LONG_TERM
        if item.access_count >= 15 and item.stage == MemoryStage.LONG_TERM:
            item.stage = MemoryStage.CONSOLIDATED
        self.store.update(item)
        return item

    def consolidate(self, agent_id: str, memory_id: str) -> MemoryItem | None:
        item = self.store.get(memory_id)
        if not item or item.agent_id != agent_id:
            return None
        old_stage = item.stage
        item.stage = MemoryStage.CONSOLIDATED
        item.strength = min(2.0, item.strength + 1.0)
        item.decay_factor = 1.0
        item.version += 1
        item.metadata["consolidated_at"] = datetime.now(timezone.utc).isoformat()
        item.metadata["previous_stage"] = old_stage.value
        self.store.update(item)
        return item

    def evolve_agent(self, agent_id: str) -> dict[str, Any]:
        items = self.store.get_by_agent(agent_id, limit=self.config.max_memories_per_agent)
        evolved = 0
        consolidated = 0
        pruned = 0

        for item in items:
            old_stage = item.stage
            self.apply_decay(item)

            if item.stage == MemoryStage.CONSOLIDATED:
                item.decay_factor = max(item.decay_factor, 0.9)

            if item.strength <= 0.05:
                item.is_valid = False
                pruned += 1

            if item.stage != old_stage:
                consolidated += 1

            self.store.update(item)
            evolved += 1

        return {
            "agent_id": agent_id,
            "evolved": evolved,
            "consolidated": consolidated,
            "pruned": pruned,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_evolution_stats(self, agent_id: str) -> dict[str, Any]:
        items = self.store.get_by_agent(agent_id, limit=self.config.max_memories_per_agent)
        if not items:
            return {"agent_id": agent_id, "total": 0, "stages": {}, "avg_retention": 0.0}

        stages: dict[str, int] = {}
        total_retention = 0.0
        for item in items:
            stage_name = item.stage.value
            stages[stage_name] = stages.get(stage_name, 0) + 1
            total_retention += self.compute_retention(item)

        return {
            "agent_id": agent_id,
            "total": len(items),
            "stages": stages,
            "avg_retention": round(total_retention / len(items), 3),
            "avg_strength": round(sum(i.strength for i in items) / len(items), 3),
            "avg_access_count": round(sum(i.access_count for i in items) / len(items), 1),
        }

    def suggest_consolidation(self, agent_id: str, limit: int = 10) -> list[MemoryItem]:
        items = self.store.get_by_agent(agent_id, limit=1000)
        candidates = [
            i for i in items
            if i.stage != MemoryStage.CONSOLIDATED
            and i.access_count >= 5
            and i.strength >= 1.0
        ]
        candidates.sort(key=lambda x: x.effective_score, reverse=True)
        return candidates[:limit]
