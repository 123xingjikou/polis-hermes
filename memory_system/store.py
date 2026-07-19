"""
Persistent SQLite-backed memory store with full-text search.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import MemoryItem, MemoryPriority, MemoryStage, MemoryType
from .config import MemoryConfig


class MemoryStore:
    def __init__(self, config: MemoryConfig | None = None):
        self.config = config or MemoryConfig()
        self.db_path = Path(self.config.db_path_str)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        c = self.conn
        c.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                level TEXT DEFAULT 'agent',
                stage TEXT DEFAULT 'working',
                priority INTEGER DEFAULT 2,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0,
                relevance_score REAL DEFAULT 1.0,
                strength REAL DEFAULT 1.0,
                decay_factor REAL DEFAULT 1.0,
                source TEXT,
                context TEXT,
                entities TEXT DEFAULT '[]',
                relationships TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                tags TEXT DEFAULT '[]',
                emotion TEXT,
                emotion_intensity REAL DEFAULT 0.5,
                is_valid INTEGER DEFAULT 1,
                reliability_score REAL DEFAULT 1.0,
                version INTEGER DEFAULT 1
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_agent_type
            ON memories(agent_id, memory_type)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_stage
            ON memories(stage) WHERE stage != 'consolidated'
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_relevance
            ON memories(relevance_score DESC)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_created
            ON memories(created_at DESC)
        """)
        if self.config.fts_enabled:
            c.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    memory_id,
                    content,
                    tags,
                    content='memories',
                    content_rowid='rowid',
                    tokenize='trigram'
                )
            """)
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(memory_id, content, tags)
                    VALUES (new.memory_id, new.content, new.tags);
                END
            """)
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, memory_id, content, tags)
                    VALUES ('delete', old.memory_id, old.content, old.tags);
                END
            """)
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, memory_id, content, tags)
                    VALUES ('delete', old.memory_id, old.content, old.tags);
                    INSERT INTO memories_fts(memory_id, content, tags)
                    VALUES (new.memory_id, new.content, new.tags);
                END
            """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS memory_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                UNIQUE(source_id, target_id, relationship)
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_edges_source
            ON memory_edges(source_id)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_edges_target
            ON memory_edges(target_id)
        """)
        c.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def insert(self, item: MemoryItem) -> None:
        c = self.conn
        c.execute(
            """INSERT INTO memories (
                memory_id, content, memory_type, agent_id, level, stage, priority,
                created_at, updated_at, last_accessed, access_count,
                relevance_score, strength, decay_factor, source, context,
                entities, relationships, metadata, tags, emotion, emotion_intensity,
                is_valid, reliability_score, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.memory_id, item.content, item.memory_type.value,
                item.agent_id, item.level, item.stage.value, item.priority.value,
                item.created_at, item.updated_at, item.last_accessed, item.access_count,
                item.relevance_score, item.strength, item.decay_factor,
                item.source, item.context,
                json.dumps(item.entities), json.dumps(item.relationships),
                json.dumps(item.metadata), json.dumps(item.tags),
                item.emotion, item.emotion_intensity,
                int(item.is_valid), item.reliability_score, item.version,
            ),
        )
        c.commit()

    def update(self, item: MemoryItem) -> None:
        item.updated_at = datetime.now(timezone.utc).isoformat()
        c = self.conn
        c.execute(
            """UPDATE memories SET
                content=?, memory_type=?, level=?, stage=?, priority=?,
                updated_at=?, last_accessed=?, access_count=?,
                relevance_score=?, strength=?, decay_factor=?,
                source=?, context=?,
                entities=?, relationships=?, metadata=?, tags=?,
                emotion=?, emotion_intensity=?,
                is_valid=?, reliability_score=?, version=?
            WHERE memory_id=?""",
            (
                item.content, item.memory_type.value,
                item.level, item.stage.value, item.priority.value,
                item.updated_at, item.last_accessed, item.access_count,
                item.relevance_score, item.strength, item.decay_factor,
                item.source, item.context,
                json.dumps(item.entities), json.dumps(item.relationships),
                json.dumps(item.metadata), json.dumps(item.tags),
                item.emotion, item.emotion_intensity,
                int(item.is_valid), item.reliability_score, item.version,
                item.memory_id,
            ),
        )
        c.commit()

    def delete(self, memory_id: str) -> bool:
        c = self.conn
        cur = c.execute("DELETE FROM memories WHERE memory_id=?", (memory_id,))
        c.commit()
        return cur.rowcount > 0

    def get(self, memory_id: str) -> MemoryItem | None:
        c = self.conn
        row = c.execute(
            "SELECT * FROM memories WHERE memory_id=?", (memory_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_item(row)

    def get_by_agent(
        self,
        agent_id: str,
        memory_type: MemoryType | None = None,
        limit: int = 100,
        offset: int = 0,
        valid_only: bool = True,
    ) -> list[MemoryItem]:
        c = self.conn
        query = "SELECT * FROM memories WHERE agent_id=?"
        params: list[Any] = [agent_id]
        if memory_type:
            query += " AND memory_type=?"
            params.append(memory_type.value)
        if valid_only:
            query += " AND is_valid=1"
        query += " ORDER BY relevance_score DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = c.execute(query, params).fetchall()
        return [self._row_to_item(r) for r in rows]

    def search_fulltext(
        self,
        query: str,
        agent_id: str | None = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        if not self.config.fts_enabled:
            return self._fallback_search(query, agent_id, limit)
        if len(query.strip()) < 3:
            return self._fallback_search(query, agent_id, limit)
        c = self.conn
        sql = """
            SELECT m.* FROM memories m
            JOIN memories_fts f ON m.memory_id = f.memory_id
            WHERE memories_fts MATCH ? AND m.is_valid=1
        """
        params: list[Any] = [query]
        if agent_id:
            sql += " AND m.agent_id=?"
            params.append(agent_id)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)
        try:
            rows = c.execute(sql, params).fetchall()
        except Exception:
            return self._fallback_search(query, agent_id, limit)
        if not rows:
            return self._fallback_search(query, agent_id, limit)
        return [self._row_to_item(r) for r in rows]

    def _fallback_search(
        self,
        query: str,
        agent_id: str | None,
        limit: int,
    ) -> list[MemoryItem]:
        c = self.conn
        sql = "SELECT * FROM memories WHERE is_valid=1 AND content LIKE ?"
        params: list[Any] = [f"%{query}%"]
        if agent_id:
            sql += " AND agent_id=?"
            params.append(agent_id)
        sql += " LIMIT ?"
        params.append(limit)
        rows = c.execute(sql, params).fetchall()
        return [self._row_to_item(r) for r in rows]

    def search_by_tags(
        self,
        tags: list[str],
        agent_id: str | None = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        c = self.conn
        conditions = " OR ".join(["tags LIKE ?"] * len(tags))
        sql = f"SELECT * FROM memories WHERE is_valid=1 AND ({conditions})"  # noqa: S608
        params: list[Any] = [f'%"{t}"%' for t in tags]
        if agent_id:
            sql += " AND agent_id=?"
            params.append(agent_id)
        sql += " ORDER BY relevance_score DESC LIMIT ?"
        params.append(limit)
        rows = c.execute(sql, params).fetchall()
        return [self._row_to_item(r) for r in rows]

    def search_by_emotion(
        self,
        emotion: str,
        agent_id: str | None = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        c = self.conn
        sql = "SELECT * FROM memories WHERE is_valid=1 AND emotion=?"
        params: list[Any] = [emotion]
        if agent_id:
            sql += " AND agent_id=?"
            params.append(agent_id)
        sql += " ORDER BY emotion_intensity DESC LIMIT ?"
        params.append(limit)
        rows = c.execute(sql, params).fetchall()
        return [self._row_to_item(r) for r in rows]

    def count_by_agent(
        self,
        agent_id: str,
        memory_type: MemoryType | None = None,
        valid_only: bool = True,
    ) -> int:
        c = self.conn
        sql = "SELECT COUNT(*) FROM memories WHERE agent_id=?"
        params: list[Any] = [agent_id]
        if memory_type:
            sql += " AND memory_type=?"
            params.append(memory_type.value)
        if valid_only:
            sql += " AND is_valid=1"
        return c.execute(sql, params).fetchone()[0]

    def get_expired(self, agent_id: str | None = None) -> list[MemoryItem]:
        c = self.conn
        sql = "SELECT * FROM memories WHERE is_valid=1 AND stage IN (?, ?)"
        params: list[Any] = [
            MemoryStage.WORKING.value,
            MemoryStage.SHORT_TERM.value,
        ]
        if agent_id:
            sql += " AND agent_id=?"
            params.append(agent_id)
        rows = c.execute(sql, params).fetchall()
        items = [self._row_to_item(r) for r in rows]
        return [i for i in items if i.is_expired]

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        weight: float = 1.0,
    ) -> None:
        c = self.conn
        c.execute(
            """INSERT OR REPLACE INTO memory_edges
               (source_id, target_id, relationship, weight, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                source_id, target_id, relationship, weight,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        c.commit()

    def get_edges(
        self,
        memory_id: str,
        direction: str = "both",
    ) -> list[dict[str, Any]]:
        c = self.conn
        results = []
        if direction in ("out", "both"):
            rows = c.execute(
                "SELECT * FROM memory_edges WHERE source_id=?", (memory_id,)
            ).fetchall()
            for r in rows:
                results.append({
                    "source": r["source_id"],
                    "target": r["target_id"],
                    "relationship": r["relationship"],
                    "weight": r["weight"],
                    "direction": "outgoing",
                })
        if direction in ("in", "both"):
            rows = c.execute(
                "SELECT * FROM memory_edges WHERE target_id=?", (memory_id,)
            ).fetchall()
            for r in rows:
                results.append({
                    "source": r["source_id"],
                    "target": r["target_id"],
                    "relationship": r["relationship"],
                    "weight": r["weight"],
                    "direction": "incoming",
                })
        return results

    def get_related_memories(
        self,
        memory_id: str,
        max_depth: int = 2,
        limit: int = 20,
    ) -> list[MemoryItem]:
        visited: set[str] = set()
        frontier: set[str] = {memory_id}
        related: list[MemoryItem] = []
        for _ in range(max_depth):
            if not frontier:
                break
            next_frontier: set[str] = set()
            for fid in frontier:
                if fid in visited:
                    continue
                visited.add(fid)
                edges = self.get_edges(fid)
                for edge in edges:
                    target = edge["target"]
                    if target not in visited:
                        next_frontier.add(target)
                        item = self.get(target)
                        if item:
                            related.append(item)
            frontier = next_frontier
        related.sort(key=lambda x: x.effective_score, reverse=True)
        return related[:limit]

    def _row_to_item(self, row: sqlite3.Row) -> MemoryItem:
        return MemoryItem(
            memory_id=row["memory_id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            agent_id=row["agent_id"],
            level=row["level"],
            stage=MemoryStage(row["stage"]),
            priority=MemoryPriority(row["priority"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_accessed=row["last_accessed"],
            access_count=row["access_count"],
            relevance_score=row["relevance_score"],
            strength=row["strength"],
            decay_factor=row["decay_factor"],
            source=row["source"],
            context=row["context"],
            entities=json.loads(row["entities"]),
            relationships=json.loads(row["relationships"]),
            metadata=json.loads(row["metadata"]),
            tags=json.loads(row["tags"]),
            emotion=row["emotion"],
            emotion_intensity=row["emotion_intensity"],
            is_valid=bool(row["is_valid"]),
            reliability_score=row["reliability_score"],
            version=row["version"],
        )

    def __enter__(self) -> MemoryStore:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
