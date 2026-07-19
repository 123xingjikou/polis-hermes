"""
Sales Promotion Data Models
============================

Dataclasses for posts, results, analytics, and platform data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PostContent:
    platform: str
    content_type: str
    title: str
    body: str
    hashtags: list[str] = field(default_factory=list)
    subreddit: str | None = None
    media_urls: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "content_type": self.content_type,
            "title": self.title,
            "body": self.body,
            "hashtags": self.hashtags,
            "subreddit": self.subreddit,
            "media_urls": self.media_urls,
        }


@dataclass
class PublishResult:
    success: bool
    platform: str
    url: str | None = None
    post_id: str | None = None
    error: str | None = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "platform": self.platform,
            "url": self.url,
            "post_id": self.post_id,
            "error": self.error,
            "created_at": self.created_at,
        }


@dataclass
class InteractResult:
    success: bool
    platform: str
    interaction_type: str
    target_id: str | None = None
    error: str | None = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "platform": self.platform,
            "interaction_type": self.interaction_type,
            "target_id": self.target_id,
            "error": self.error,
            "created_at": self.created_at,
        }


@dataclass
class AnalyticsReport:
    total_posts: int = 0
    success_rate: float = 0.0
    total_interactions: int = 0
    platform_breakdown: dict[str, int] = field(default_factory=dict)
    content_performance: dict[str, dict[str, int]] = field(default_factory=dict)
    date_range: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_posts": self.total_posts,
            "success_rate": self.success_rate,
            "total_interactions": self.total_interactions,
            "platform_breakdown": self.platform_breakdown,
            "content_performance": self.content_performance,
            "date_range": self.date_range,
        }


@dataclass
class DateRange:
    start: datetime
    end: datetime

    def to_dict(self) -> dict[str, str]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
        }
