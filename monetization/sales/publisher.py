"""
Social Publisher
=================

High-level publisher that routes PostContent to the right platform adapter.
"""

from __future__ import annotations

import logging

from .models import PostContent, PublishResult, InteractResult
from .platforms import get_platform, BasePlatform, PLAYWRIGHT_AVAILABLE

logger = logging.getLogger(__name__)


class SocialPublisher:
    def __init__(self, dry_run: bool = True, platform_name: str | None = None):
        self._dry_run = dry_run
        self._platforms: dict[str, BasePlatform] = {}
        self._default_platform_name = platform_name

    def _get_platform(self, platform_name: str | None = None) -> BasePlatform:
        name = platform_name or self._default_platform_name or "mock"
        if name not in self._platforms:
            self._platforms[name] = get_platform(name, dry_run=self._dry_run)
        return self._platforms[name]

    async def publish(self, content: PostContent) -> PublishResult:
        """Publish content to its specified platform."""
        platform = self._get_platform(content.platform)
        logger.info("Publishing to %s: %s", content.platform, content.title[:60])
        try:
            return await platform.post(content)
        except Exception as e:
            logger.error("Publish to %s failed: %s", content.platform, e)
            return PublishResult(success=False, platform=content.platform, error=str(e))

    async def interact(self, platform: str, post_id: str) -> InteractResult:
        """Interact with a post on the specified platform."""
        adapter = self._get_platform(platform)
        try:
            return await adapter.interact(post_id)
        except Exception as e:
            logger.error("Interaction with %s failed: %s", platform, e)
            return InteractResult(
                success=False,
                platform=platform,
                interaction_type="interact",
                target_id=post_id,
                error=str(e),
            )

    @property
    def dry_run(self) -> bool:
        return self._dry_run

    @property
    def playwright_available(self) -> bool:
        return PLAYWRIGHT_AVAILABLE
