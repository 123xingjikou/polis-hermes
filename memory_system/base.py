"""
Core data types for the memory system.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    EMOTIONAL = "emotional"


class MemoryStage(str, Enum):
    WORKING = "working"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    CONSOLIDATED = "consolidated"


class MemoryPriority(int, Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class MemoryItem:
    content: str
    memory_type: MemoryType
    agent_id: str
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    level: str = "agent"
    stage: MemoryStage = MemoryStage.WORKING
    priority: MemoryPriority = MemoryPriority.NORMAL
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_accessed: str | None = None
    access_count: int = 0
    relevance_score: float = 1.0
    strength: float = 1.0
    decay_factor: float = 1.0
    source: str | None = None
    context: str | None = None
    entities: list[str] = field(default_factory=list)
    relationships: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    emotion: str | None = None
    emotion_intensity: float = 0.5
    is_valid: bool = True
    reliability_score: float = 1.0
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "agent_id": self.agent_id,
            "level": self.level,
            "stage": self.stage.value,
            "priority": self.priority.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "relevance_score": self.relevance_score,
            "strength": self.strength,
            "decay_factor": self.decay_factor,
            "source": self.source,
            "context": self.context,
            "entities": self.entities,
            "relationships": self.relationships,
            "metadata": self.metadata,
            "tags": self.tags,
            "emotion": self.emotion,
            "emotion_intensity": self.emotion_intensity,
            "is_valid": self.is_valid,
            "reliability_score": self.reliability_score,
            "version": self.version,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> MemoryItem:
        return MemoryItem(
            memory_id=data.get("memory_id", str(uuid.uuid4())),
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            agent_id=data["agent_id"],
            level=data.get("level", "agent"),
            stage=MemoryStage(data.get("stage", "working")),
            priority=MemoryPriority(data.get("priority", 2)),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            last_accessed=data.get("last_accessed"),
            access_count=data.get("access_count", 0),
            relevance_score=data.get("relevance_score", 1.0),
            strength=data.get("strength", 1.0),
            decay_factor=data.get("decay_factor", 1.0),
            source=data.get("source"),
            context=data.get("context"),
            entities=data.get("entities", []),
            relationships=data.get("relationships", []),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            emotion=data.get("emotion"),
            emotion_intensity=data.get("emotion_intensity", 0.5),
            is_valid=data.get("is_valid", True),
            reliability_score=data.get("reliability_score", 1.0),
            version=data.get("version", 1),
        )

    def mark_accessed(self) -> None:
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc).isoformat()

    def strengthen(self, amount: float) -> None:
        self.strength = min(2.0, self.strength + amount)
        self.version += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def weaken(self, amount: float) -> None:
        self.strength = max(0.0, self.strength - amount)
        if self.strength <= 0.01:
            self.is_valid = False
        self.updated_at = datetime.now(timezone.utc).isoformat()

    @property
    def effective_score(self) -> float:
        return self.relevance_score * self.strength * self.decay_factor * self.reliability_score

    @property
    def is_expired(self) -> bool:
        if self.stage == MemoryStage.WORKING:
            return False
        try:
            created = datetime.fromisoformat(self.created_at)
            age = datetime.now(timezone.utc) - created
            if self.stage == MemoryStage.SHORT_TERM:
                return age > timedelta(hours=2)
            if self.stage == MemoryStage.LONG_TERM:
                return age > timedelta(days=30)
        except (ValueError, TypeError):
            pass
        return False
