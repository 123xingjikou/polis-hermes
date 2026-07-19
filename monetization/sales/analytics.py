"""
Analytics Tracker
==================

SQLite-backed analytics for tracking posts, interactions, and performance.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime
from typing import Any

from .models import (
    PostContent,
    PublishResult,
    InteractResult,
    AnalyticsReport,
    DateRange,
)

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(
    os.path.expanduser("~"), ".polis", "sales", "sales_analytics.db"
)


class AnalyticsTracker:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        db_dir = os.path.dirname(self._db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                content_type TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                hashtags TEXT,
                subreddit TEXT,
                success INTEGER NOT NULL DEFAULT 0,
                url TEXT,
                post_id TEXT,
                error TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                interaction_type TEXT NOT NULL,
                target_id TEXT,
                status TEXT NOT NULL DEFAULT 'success',
                post_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform);
            CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);
            CREATE INDEX IF NOT EXISTS idx_interactions_platform ON interactions(platform);
            CREATE INDEX IF NOT EXISTS idx_interactions_created ON interactions(created_at);
        """)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    async def record_post(self, content: PostContent, result: PublishResult) -> str:
        import uuid
        post_id = f"post_{uuid.uuid4().hex[:12]}"
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO posts
                   (id, platform, content_type, title, body, hashtags,
                    subreddit, success, url, post_id, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    post_id,
                    content.platform,
                    content.content_type,
                    content.title,
                    content.body,
                    ",".join(content.hashtags) if content.hashtags else "",
                    content.subreddit,
                    1 if result.success else 0,
                    result.url,
                    result.post_id,
                    result.error,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return post_id

    async def record_interaction(
        self,
        interaction_type: str,
        target_id: str,
        status: str,
        platform: str,
        post_id: str | None = None,
    ) -> str:
        import uuid
        iid = f"int_{uuid.uuid4().hex[:12]}"
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO interactions
                   (id, platform, interaction_type, target_id, status, post_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (iid, platform, interaction_type, target_id, status, post_id),
            )
            conn.commit()
        finally:
            conn.close()
        return iid

    async def generate_report(self, date_range: DateRange) -> AnalyticsReport:
        conn = self._get_conn()
        try:
            start_str = date_range.start.isoformat()
            end_str = date_range.end.isoformat()
            rows = conn.execute(
                """SELECT platform, content_type, success FROM posts
                   WHERE created_at BETWEEN ? AND ?""",
                (start_str, end_str),
            ).fetchall()
            total_posts = len(rows)
            successes = sum(1 for r in rows if r["success"])
            success_rate = (successes / total_posts) if total_posts > 0 else 0.0
            platform_breakdown = self._group_by_platform(rows)
            content_performance = self._group_by_content_type(rows)
            interaction_rows = conn.execute(
                """SELECT platform, status FROM interactions
                   WHERE created_at BETWEEN ? AND ?""",
                (start_str, end_str),
            ).fetchall()
            total_interactions = len(interaction_rows)
            return AnalyticsReport(
                total_posts=total_posts,
                success_rate=success_rate,
                total_interactions=total_interactions,
                platform_breakdown=platform_breakdown,
                content_performance=content_performance,
                date_range={"start": start_str, "end": end_str},
            )
        finally:
            conn.close()

    def _group_by_platform(self, rows: list[sqlite3.Row]) -> dict[str, int]:
        result: dict[str, int] = {}
        for r in rows:
            platform = r["platform"]
            result[platform] = result.get(platform, 0) + 1
        return result

    def _group_by_content_type(self, rows: list[sqlite3.Row]) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        for r in rows:
            ct = r["content_type"]
            if ct not in result:
                result[ct] = {"total": 0, "success": 0}
            result[ct]["total"] += 1
            if r["success"]:
                result[ct]["success"] += 1
        return result

    def _calc_success_rate(self, total: int, success: int) -> float:
        return (success / total) if total > 0 else 0.0
