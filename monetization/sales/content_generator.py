"""
Content Generator
==================

Generates social media posts using LLM (when available) or template fallback.
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timedelta
from typing import Any

from .models import PostContent
from .templates import get_template, format_for_twitter, format_for_reddit, format_for_hn

logger = logging.getLogger(__name__)

TOPIC_POOL: list[dict[str, str]] = [
    {"topic": "autonomous AI agents", "tag": "AIAgents"},
    {"topic": "multi-agent systems", "tag": "MultiAgent"},
    {"topic": "cognitive computing", "tag": "CognitiveComputing"},
    {"topic": "agent economy", "tag": "AgentEconomy"},
    {"topic": "decentralized AI", "tag": "DecentralizedAI"},
    {"topic": "AI governance", "tag": "AIGovernance"},
    {"topic": "adaptive systems", "tag": "AdaptiveSystems"},
    {"topic": "emergent behavior", "tag": "EmergentBehavior"},
    {"topic": "self-organizing systems", "tag": "SelfOrganizing"},
    {"topic": "digital twins", "tag": "DigitalTwins"},
]

CONTENT_TYPES = ["tutorial", "story", "engagement"]

PLATFORM_FORMATTERS = {
    "twitter": format_for_twitter,
    "reddit": format_for_reddit,
    "hn": format_for_hn,
}


class ContentGenerator:
    def __init__(self, llm_capability: Any | None = None):
        self._llm = llm_capability

    async def generate(self, platform: str, content_type: str, topic: str) -> PostContent:
        if self._llm is not None and getattr(self._llm, "mode", "fallback") == "real":
            return await self._generate_with_llm(platform, content_type, topic)
        return self._generate_with_template(platform, content_type, topic)

    async def _generate_with_llm(self, platform: str, content_type: str, topic: str) -> PostContent:
        prompt = (
            f"Write a social media post about '{topic}' for {platform}.\n"
            f"Content type: {content_type}.\n"
            f"Context: Polis-Hermes is an autonomous cognitive city project.\n"
            f"Respond in JSON format with keys: title, body, hashtags."
        )
        try:
            result = await self._llm.execute({"prompt": prompt, "platform": platform})
            if isinstance(result, dict) and "body" in result:
                title = result.get("title", f"{topic.title()} - Polis-Hermes")
                body_raw = result.get("body", "")
                hashtags = result.get("hashtags", ["#PolisHermes", "#AI"])
                formatter = PLATFORM_FORMATTERS.get(platform, lambda x: x)
                body = formatter(body_raw)
                topic_entry = next((t for t in TOPIC_POOL if t["topic"] == topic), None)
                tags = [f"#{topic_entry['tag']}", "#PolisHermes"] if topic_entry else ["#PolisHermes"]
                return PostContent(
                    platform=platform,
                    content_type=content_type,
                    title=title,
                    body=body,
                    hashtags=hashtags + tags,
                    subreddit="PolisHermes" if platform == "reddit" else None,
                    media_urls=["https://github.com/123xingjikou/polis-hermes"] if platform in ("hn", "reddit") else None,
                )
        except Exception as e:
            logger.warning("LLM generation failed, falling back to template: %s", e)
        return self._generate_with_template(platform, content_type, topic)

    def _generate_with_template(self, platform: str, content_type: str, topic: str) -> PostContent:
        templates = get_template(content_type)
        if not templates:
            templates = get_template("story")
        template = random.choice(templates)
        topic_entry = next((t for t in TOPIC_POOL if t["topic"] == topic), None)
        topic_tag = topic_entry["tag"] if topic_entry else topic.replace(" ", "")
        filled = template.format(topic=topic, topic_tag=topic_tag)
        formatter = PLATFORM_FORMATTERS.get(platform, lambda x: x)
        body = formatter(filled)
        title = f"{topic.title()} - Polis-Hermes"
        hashtags = [f"#{topic_tag}", "#PolisHermes"]
        subreddit = "PolisHermes" if platform == "reddit" else None
        media_urls = ["https://github.com/123xingjikou/polis-hermes"] if platform in ("hn", "reddit") else None
        return PostContent(
            platform=platform,
            content_type=content_type,
            title=title,
            body=body,
            hashtags=hashtags,
            subreddit=subreddit,
            media_urls=media_urls,
        )

    async def generate_calendar(
        self, days: int, platform: str | None = None
    ) -> list[PostContent]:
        """Generate content calendar for the given number of days.
        
        Args:
            days: Number of days to generate content for.
            platform: Optional platform filter ('twitter', 'reddit', 'hn').
        """
        calendar: list[PostContent] = []
        platforms_by_day: dict[int, list[tuple[str, str]]] = {
            0: [("twitter", "engagement"), ("reddit", "tutorial")],
            1: [("twitter", "story")],
            2: [("hn", "engagement"), ("twitter", "tutorial")],
            3: [("twitter", "engagement"), ("reddit", "story")],
            4: [("twitter", "tutorial")],
            5: [("reddit", "engagement"), ("twitter", "story")],
            6: [("twitter", "engagement")],
        }
        for day_offset in range(days):
            day_index = day_offset % 7
            entries = platforms_by_day.get(day_index, [("twitter", "engagement")])
            for p, content_type in entries:
                if platform and p != platform:
                    continue
                topic_entry = random.choice(TOPIC_POOL)
                content = await self.generate(p, content_type, topic_entry["topic"])
                calendar.append(content)
        return calendar
