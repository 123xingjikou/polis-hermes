"""
Sales Agent
============

Autonomous sales/promotion agent for Polis-Hermes.
Extends CityResident with 4 capabilities: generate_content, publish_post, interact, analyze.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict

from city.core.resident import CityResident
from city.capabilities.llm_impl import LLMCapability

from .content_generator import ContentGenerator
from .publisher import SocialPublisher
from .analytics import AnalyticsTracker
from .models import (
    PostContent,
    PublishResult,
    InteractResult,
    AnalyticsReport,
    DateRange,
)

logger = logging.getLogger(__name__)

PROMOTER_PERSONALITY: dict[str, float] = {
    "openness": 0.85,
    "confidence": 0.70,
    "aggressiveness": 0.30,
}

PROMOTER_SKILLS: dict[str, float] = {
    "content_creation": 0.9,
    "technical_writing": 0.85,
    "community_engagement": 0.8,
}


class SalesAgent(CityResident):
    def __init__(
        self,
        name: str = "Hermes-Promoter",
        llm_capability: LLMCapability | None = None,
        dry_run: bool = True,
        analytics_db_path: str | None = None,
        personality: dict[str, float] | None = None,
        skills: dict[str, float] | None = None,
    ):
        person = personality if personality is not None else PROMOTER_PERSONALITY
        sk = skills if skills is not None else PROMOTER_SKILLS
        super().__init__(
            name=name,
            personality=person,
            skills=sk,
            role="promoter",
        )
        self._llm = llm_capability or LLMCapability()
        self._content_gen = ContentGenerator(self._llm)
        self._publisher = SocialPublisher(dry_run=dry_run)
        self._analytics = AnalyticsTracker(db_path=analytics_db_path) if analytics_db_path is not None else AnalyticsTracker()
        self._setup_capabilities()

    def _setup_capabilities(self) -> None:
        self.capabilities["generate_content"] = self._generate_content
        self.capabilities["publish_post"] = self._publish_post
        self.capabilities["interact"] = self._interact
        self.capabilities["analyze"] = self._analyze

    async def _generate_content(self, context: dict[str, Any]) -> dict[str, Any]:
        platform = context.get("platform", "twitter")
        content_type = context.get("content_type", "engagement")
        topic = context.get("topic", "autonomous AI agents")
        content = await self._content_gen.generate(platform, content_type, topic)
        return {"status": "ok", "content": content.to_dict()}

    async def _publish_post(self, context: dict[str, Any]) -> dict[str, Any]:
        content_data = context.get("content", {})
        if isinstance(content_data, dict):
            content = PostContent(
                platform=content_data.get("platform", "mock"),
                content_type=content_data.get("content_type", "engagement"),
                title=content_data.get("title", ""),
                body=content_data.get("body", ""),
                hashtags=content_data.get("hashtags", []),
                subreddit=content_data.get("subreddit"),
                media_urls=content_data.get("media_urls"),
            )
        elif isinstance(content_data, PostContent):
            content = content_data
        else:
            return {"status": "error", "message": "Invalid content data"}
        result = await self._publisher.publish(content)
        await self._analytics.record_post(content, result)
        return {"status": "ok" if result.success else "error", "result": result.to_dict()}

    async def _interact(self, context: dict[str, Any]) -> dict[str, Any]:
        platform = context.get("platform", "twitter")
        post_id = context.get("post_id", "")
        result = await self._publisher.interact(platform, post_id)
        await self._analytics.record_interaction(
            interaction_type=result.interaction_type,
            target_id=result.target_id or post_id,
            status="success" if result.success else "failure",
            platform=platform,
        )
        return {"status": "ok" if result.success else "error", "result": result.to_dict()}

    async def _analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        from datetime import datetime, timedelta, timezone
        days = context.get("days", 30)
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        date_range = DateRange(start=start, end=end)
        report = await self._analytics.generate_report(date_range)
        return {"status": "ok", "report": report.to_dict()}

    def __repr__(self) -> str:
        return (
            f"SalesAgent(name={self.name!r}, role={self.role!r}, "
            f"dry_run={self._publisher.dry_run})"
        )


def create_sales_agent(
    name: str = "Hermes-Promoter",
    dry_run: bool = True,
    llm_capability: LLMCapability | None = None,
    analytics_db_path: str | None = None,
    personality: dict[str, float] | None = None,
    skills: dict[str, float] | None = None,
) -> SalesAgent:
    """Factory function to create a SalesAgent with standard configuration."""
    return SalesAgent(
        name=name,
        llm_capability=llm_capability,
        dry_run=dry_run,
        analytics_db_path=analytics_db_path,
        personality=personality,
        skills=skills,
    )
