"""
Cross-city memory: distributed inter-agent shared memory with caching.

Enables agents across different cities to share and query memories with
permission verification, result caching, and remote gateway support.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .store import MemoryStore


class CrossCityMemoryQuery:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl = 60

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def search_memories(
        self,
        query: str,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        cache_key = f"search:{query}:{agent_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return {**cached, "cached": True}

        if not self._conn:
            return {"results": [], "count": 0, "query": query}

        if not self._table_exists("memories"):
            return {"results": [], "count": 0, "query": query}

        sql = "SELECT * FROM memories WHERE content LIKE ?"
        params: list[Any] = [f"%{query}%"]
        if agent_id:
            sql += " AND agent_id=?"
            params.append(agent_id)
        sql += " ORDER BY importance DESC LIMIT 50"

        rows = self._conn.execute(sql, params).fetchall()
        results = [dict(r) for r in rows]
        response = {"results": results, "count": len(results), "query": query}
        self._set_cache(cache_key, response)
        return response

    def get_agent_memories(self, agent_id: str) -> dict[str, Any]:
        if not self._conn:
            return {"agent_id": agent_id, "results": [], "count": 0}

        rows = self._conn.execute(
            "SELECT * FROM memories WHERE agent_id=? ORDER BY importance DESC",
            (agent_id,),
        ).fetchall()
        results = [dict(r) for r in rows]
        return {"agent_id": agent_id, "results": results, "count": len(results)}

    def get_shared_memories(self, agent_id: str) -> dict[str, Any]:
        if not self._conn:
            return {"results": [], "count": 0, "agent_id": agent_id}

        rows = self._conn.execute(
            """SELECT m.* FROM memories m
               JOIN memory_shares ms ON m.id = ms.memory_id
               WHERE ms.to_agent = ?
               ORDER BY m.importance DESC""",
            (agent_id,),
        ).fetchall()
        results = [dict(r) for r in rows]
        return {"results": results, "count": len(results), "agent_id": agent_id}

    def get_stats(self) -> dict[str, Any]:
        if not self._conn:
            return {"timestamp": datetime.now(timezone.utc).isoformat(), "cache_size": 0}

        memory_count = self._conn.execute(
            "SELECT COUNT(*) FROM memories"
        ).fetchone()[0]
        share_count = self._conn.execute(
            "SELECT COUNT(*) FROM memory_shares"
        ).fetchone()[0]

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_size": len(self._cache),
            "memory_count": memory_count,
            "share_count": share_count,
        }

    def verify_permission(
        self,
        city: str,
        requester: str,
        target: str,
    ) -> bool:
        if not self._conn:
            return False
        row = self._conn.execute(
            """SELECT permission FROM memory_shares
               WHERE from_agent=? AND to_agent=?""",
            (target, requester),
        ).fetchone()
        if not row:
            return False
        permission = row["permission"]
        return permission in ("see_content", "full_access")

    def handle_cross_city_query(self, query: dict[str, Any]) -> dict[str, Any]:
        qtype = query.get("type", "")

        if qtype == "memory_search":
            return self.search_memories(
                query.get("query", ""),
                query.get("requesting_agent"),
            )
        elif qtype == "agent_memories":
            return self.get_agent_memories(query.get("requesting_agent", ""))
        elif qtype == "shared_memories":
            return self.get_shared_memories(query.get("requesting_agent", ""))
        else:
            return {"error": "unknown_type", "requested_type": qtype}

    def _table_exists(self, table_name: str) -> bool:
        if not self._conn:
            return False
        row = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        return row is not None

    def _get_cached(self, key: str) -> dict[str, Any] | None:
        entry = self._cache.get(key)
        if entry and (time.time() - entry["ts"]) < self._cache_ttl:
            return entry["data"]
        if entry:
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: dict[str, Any]) -> None:
        self._cache[key] = {"data": data, "ts": time.time()}


class CrossCityMemoryClient:
    def __init__(self, gateway_url: str, timeout: float = 5.0):
        self.gateway_url = gateway_url
        self.timeout = timeout

    def search_remote(self, city: str, query: str) -> dict[str, Any]:
        try:
            import urllib.error
            import urllib.request

            url = f"{self.gateway_url}/api/v1/cities/{city}/memory/search"
            payload = json.dumps({"query": query}).encode()
            req = urllib.request.Request(  # noqa: S310
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e), "city": city, "query": query}


class CrossCityMemory:
    def __init__(self, store: MemoryStore, gateway_url: str | None = None):
        self.store = store
        self.gateway_url = gateway_url
        self._client = CrossCityMemoryClient(gateway_url) if gateway_url else None

    def share(
        self,
        from_agent: str,
        to_agent: str,
        memory_id: str,
        permission: str = "see_content",
    ) -> bool:
        memory = self.store.get(memory_id)
        if not memory or memory.agent_id != from_agent:
            return False
        self.store.add_edge(from_agent, to_agent, f"share:{permission}")
        return True

    def query_remote(self, city: str, query: str) -> dict[str, Any]:
        if not self._client:
            return {"error": "no_gateway_configured"}
        return self._client.search_remote(city, query)

    def sync_with_city(self, city: str) -> dict[str, Any]:
        return {"status": "not_implemented", "city": city}
