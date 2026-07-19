"""
Reliability scoring: memory quality and agent trustworthiness evaluation.

Scores memories and agents on multiple dimensions: SLA compliance,
timeout rates, error patterns, consistency, and trend analysis.
Inspired by traditional reliability engineering adapted for AI agents.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from .store import MemoryStore


@dataclass
class ReliabilityScore:
    agent_id: str
    overall_score: float
    sla_score: float = 0.0
    timeout_score: float = 0.0
    error_score: float = 0.0
    consistency_score: float = 0.0
    trend_score: float = 0.0
    reliability_label: str = "unknown"
    error_breakdown: dict[str, int] = field(default_factory=dict)
    sample_count: int = 0
    computed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "overall_score": round(self.overall_score, 3),
            "sla_score": round(self.sla_score, 3),
            "timeout_score": round(self.timeout_score, 3),
            "error_score": round(self.error_score, 3),
            "consistency_score": round(self.consistency_score, 3),
            "trend_score": round(self.trend_score, 3),
            "reliability_label": self.reliability_label,
            "error_breakdown": self.error_breakdown,
            "sample_count": self.sample_count,
            "computed_at": self.computed_at,
        }


class AgentReliabilityScorer:
    ERROR_CATEGORIES: ClassVar[dict[str, str]] = {
        "ImportError": "system",
        "ModuleNotFoundError": "system",
        "AttributeError": "system",
        "TypeError": "system",
        "SyntaxError": "system",
        "NameError": "system",
        "TimeoutError": "network",
        "ConnectionError": "network",
        "ConnectionRefusedError": "network",
        "ConnectionResetError": "network",
        "Timeout": "network",
        "ValueError": "business",
        "KeyError": "business",
        "IndexError": "business",
        "AssertionError": "business",
        "PermissionError": "business",
    }

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else None
        self._conn: sqlite3.Connection | None = None
        if self.db_path:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _classify_error(self, error_type: str) -> str:
        return self.ERROR_CATEGORIES.get(error_type, "other")

    def compute_reliability(self, agent_id: str) -> ReliabilityScore:
        if not self._conn:
            return ReliabilityScore(agent_id=agent_id, overall_score=0.5, reliability_label="unknown")

        session_data = self._fetch_session_data(agent_id)
        if not session_data:
            return ReliabilityScore(agent_id=agent_id, overall_score=0.5, reliability_label="unknown")

        timeout_score = self._compute_timeout_score(session_data)
        error_score = self._compute_error_score(session_data)
        consistency_score = self._compute_consistency_score(session_data)
        trend_score = self._compute_trend_score(session_data)
        sla_score = self._compute_sla_score(session_data)
        error_breakdown = self._compute_error_breakdown(session_data)

        overall = (
            timeout_score * 0.25
            + error_score * 0.25
            + consistency_score * 0.2
            + trend_score * 0.15
            + sla_score * 0.15
        )

        label = self._score_to_label(overall)

        return ReliabilityScore(
            agent_id=agent_id,
            overall_score=round(overall, 4),
            sla_score=round(sla_score, 4),
            timeout_score=round(timeout_score, 4),
            error_score=round(error_score, 4),
            consistency_score=round(consistency_score, 4),
            trend_score=round(trend_score, 4),
            reliability_label=label,
            error_breakdown=error_breakdown,
            sample_count=len(session_data),
        )

    def apply_to_trust(
        self,
        trust: float,
        reliability: float,
        min_reliability: float = 0.0,
    ) -> float:
        if reliability >= min_reliability:
            return trust
        penalty = reliability / max(min_reliability, 0.01)
        return max(0.0, trust * penalty)

    def batch_reliability(self, agent_ids: list[str]) -> list[ReliabilityScore]:
        return [self.compute_reliability(aid) for aid in agent_ids]

    def get_low_reliability_agents(self, threshold: float = 0.3) -> list[dict[str, Any]]:
        if not self._conn:
            return []
        rows = self._conn.execute(
            "SELECT DISTINCT sender FROM session_log"
        ).fetchall()
        results = []
        for row in rows:
            score = self.compute_reliability(row["sender"])
            if score.overall_score < threshold:
                results.append(score.to_dict())
        return results

    def _fetch_session_data(self, agent_id: str) -> list[sqlite3.Row]:
        if not self._conn:
            return []
        return self._conn.execute(
            "SELECT * FROM session_log WHERE sender=? ORDER BY timestamp",
            (agent_id,),
        ).fetchall()

    def _compute_timeout_score(self, data: list[sqlite3.Row]) -> float:
        if not data:
            return 0.5
        timeouts = sum(1 for r in data if r["status"] == "timeout")
        return max(0.0, 1.0 - timeouts / len(data))

    def _compute_error_score(self, data: list[sqlite3.Row]) -> float:
        if not data:
            return 0.5
        errors = sum(1 for r in data if r["status"] in ("error", "failed"))
        return max(0.0, 1.0 - errors / len(data))

    def _compute_consistency_score(self, data: list[sqlite3.Row]) -> float:
        if len(data) < 2:
            return 0.5
        times = [r["response_time_ms"] for r in data if r["response_time_ms"] is not None]
        if len(times) < 2:
            return 0.5
        mean = sum(times) / len(times)
        variance = sum((t - mean) ** 2 for t in times) / len(times)
        std = variance ** 0.5
        cv = std / mean if mean > 0 else 1.0
        return max(0.0, min(1.0, 1.0 - cv))

    def _compute_trend_score(self, data: list[sqlite3.Row]) -> float:
        if len(data) < 4:
            return 0.5
        mid = len(data) // 2
        first_half = data[:mid]
        second_half = data[mid:]
        first_errors = sum(1 for r in first_half if r["status"] in ("error", "timeout", "failed"))
        second_errors = sum(1 for r in second_half if r["status"] in ("error", "timeout", "failed"))
        first_rate = first_errors / max(len(first_half), 1)
        second_rate = second_errors / max(len(second_half), 1)
        if second_rate < first_rate:
            return min(1.0, 0.7 + (first_rate - second_rate))
        elif second_rate > first_rate:
            return max(0.0, 0.7 - (second_rate - first_rate))
        return 0.7

    def _compute_sla_score(self, data: list[sqlite3.Row]) -> float:
        if not data:
            return 0.5
        sla_threshold_ms = 2000
        within_sla = sum(
            1 for r in data
            if r["response_time_ms"] is not None and r["response_time_ms"] <= sla_threshold_ms
        )
        return within_sla / len(data)

    def _compute_error_breakdown(self, data: list[sqlite3.Row]) -> dict[str, int]:
        breakdown: dict[str, int] = {}
        for r in data:
            if r["status"] in ("error", "failed"):
                status = r["status"]
                breakdown[status] = breakdown.get(status, 0) + 1
        return breakdown

    @staticmethod
    def _score_to_label(score: float) -> str:
        if score >= 0.9:
            return "excellent"
        if score >= 0.7:
            return "high"
        if score >= 0.5:
            return "medium"
        if score >= 0.3:
            return "low"
        return "critical"


class ReliabilityScanner:
    def __init__(self, store: MemoryStore, threshold: float = 0.4):
        self.store = store
        self.threshold = threshold

    def scan(self, agent_id: str) -> list[dict[str, Any]]:
        items = self.store.get_by_agent(agent_id, limit=1000)
        unreliable = []
        for item in items:
            if item.reliability_score < self.threshold:
                unreliable.append({
                    "memory_id": item.memory_id,
                    "content": item.content[:100],
                    "reliability_score": item.reliability_score,
                    "type": item.memory_type.value,
                })
        return sorted(unreliable, key=lambda x: x["reliability_score"])

    def flag_unreliable(self, agent_id: str) -> int:
        items = self.store.get_by_agent(agent_id, limit=1000)
        count = 0
        for item in items:
            if item.reliability_score < self.threshold and item.is_valid:
                item.is_valid = False
                self.store.update(item)
                count += 1
        return count
