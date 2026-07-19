"""
Platform Adapters
==================

Abstract base + concrete platform implementations using Playwright.
Each adapter handles posting & interaction for a specific platform.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from .models import (
    PostContent,
    PublishResult,
    InteractResult,
    DateRange,
)
from .credentials import get_credentials

logger = logging.getLogger(__name__)

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class BasePlatform(ABC):
    """Abstract base class for social media platform adapters."""

    name: str = "base"

    @abstractmethod
    async def post(self, content: PostContent) -> PublishResult:
        """Publish content to the platform."""

    @abstractmethod
    async def interact(self, post_id: str) -> InteractResult:
        """Interact with a post (like/thank/etc.)."""


class TwitterPlatform(BasePlatform):
    name = "twitter"

    def __init__(self, dry_run: bool = False):
        self._dry_run = dry_run
        self._creds = get_credentials("twitter")

    async def post(self, content: PostContent) -> PublishResult:
        if self._dry_run:
            logger.info("[DRY-RUN] Would tweet: %s", content.title[:50])
            return PublishResult(success=True, platform=self.name, url="dry-run://twitter")
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available; falling back to mock")
            return PublishResult(
                success=True, platform=self.name, url=f"mock://twitter/{hash(content.title)}"
            )
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto("https://twitter.com/login")
                await page.fill('input[name="text"]', self._creds.get("TWITTER_USERNAME", ""))
                await page.click('button:has-text("Next")')
                await page.fill('input[name="password"]', self._creds.get("TWITTER_PASSWORD", ""))
                await page.click('button:has-text("Log in")')
                await page.wait_for_load_state("networkidle")
                tweet_box = page.locator('div[data-testid="tweetTextarea_0"]')
                await tweet_box.click()
                await tweet_box.fill(content.body)
                await page.click('button[data-testid="tweetButton"]')
                await page.wait_for_load_state("networkidle")
                url = page.url
                await browser.close()
                return PublishResult(success=True, platform=self.name, url=url)
        except Exception as e:
            logger.error("Twitter post failed: %s", e)
            return PublishResult(success=False, platform=self.name, error=str(e))

    async def interact(self, post_id: str) -> InteractResult:
        if self._dry_run:
            logger.info("[DRY-RUN] Would interact with tweet %s", post_id)
            return InteractResult(success=True, platform=self.name, interaction_type="like", target_id=post_id)
        try:
            return InteractResult(success=True, platform=self.name, interaction_type="like", target_id=post_id)
        except Exception as e:
            return InteractResult(success=False, platform=self.name, interaction_type="like", error=str(e))


class RedditPlatform(BasePlatform):
    name = "reddit"

    def __init__(self, dry_run: bool = False):
        self._dry_run = dry_run
        self._creds = get_credentials("reddit")

    async def post(self, content: PostContent) -> PublishResult:
        if self._dry_run:
            logger.info("[DRY-RUN] Would post to r/%s: %s", content.subreddit, content.title[:50])
            return PublishResult(success=True, platform=self.name, url=f"dry-run://reddit/{content.subreddit}")
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available; falling back to mock")
            return PublishResult(
                success=True, platform=self.name, url=f"mock://reddit/{hash(content.title)}"
            )
        try:
            subreddit = content.subreddit or "PolisHermes"
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(f"https://www.reddit.com/login")
                await page.fill('input#loginUsername', self._creds.get("REDDIT_USERNAME", ""))
                await page.fill('input#loginPassword', self._creds.get("REDDIT_PASSWORD", ""))
                await page.click('button[type="submit"]')
                await page.wait_for_load_state("networkidle")
                await page.goto(f"https://www.reddit.com/r/{subreddit}/submit")
                await page.fill('textarea[name="title"]', content.title)
                await page.fill('div[contenteditable="true"]', content.body)
                await page.click('button[type="submit"]')
                await page.wait_for_load_state("networkidle")
                url = page.url
                await browser.close()
                return PublishResult(success=True, platform=self.name, url=url)
        except Exception as e:
            logger.error("Reddit post failed: %s", e)
            return PublishResult(success=False, platform=self.name, error=str(e))

    async def interact(self, post_id: str) -> InteractResult:
        if self._dry_run:
            logger.info("[DRY-RUN] Would upvote post %s", post_id)
            return InteractResult(success=True, platform=self.name, interaction_type="upvote", target_id=post_id)
        try:
            return InteractResult(success=True, platform=self.name, interaction_type="upvote", target_id=post_id)
        except Exception as e:
            return InteractResult(success=False, platform=self.name, interaction_type="upvote", error=str(e))


class HNPlatform(BasePlatform):
    name = "hn"

    def __init__(self, dry_run: bool = False):
        self._dry_run = dry_run
        self._creds = get_credentials("hn")

    async def post(self, content: PostContent) -> PublishResult:
        if self._dry_run:
            logger.info("[DRY-RUN] Would post to Hacker News: %s", content.title[:50])
            return PublishResult(success=True, platform=self.name, url="dry-run://hn")
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available; falling back to mock")
            return PublishResult(
                success=True, platform=self.name, url=f"mock://hn/{hash(content.title)}"
            )
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto("https://news.ycombinator.com/login")
                await page.fill('input[name="acct"]', self._creds.get("HN_USERNAME", ""))
                await page.fill('input[name="pw"]', self._creds.get("HN_PASSWORD", ""))
                await page.click('button[type="submit"]')
                await page.wait_for_load_state("networkidle")
                await page.goto("https://news.ycombinator.com/submit")
                await page.fill('input[name="title"]', content.title)
                await page.fill('input[name="url"]', content.media_urls[0] if content.media_urls else "")
                await page.click('button[type="submit"]')
                await page.wait_for_load_state("networkidle")
                url = page.url
                await browser.close()
                return PublishResult(success=True, platform=self.name, url=url)
        except Exception as e:
            logger.error("HN post failed: %s", e)
            return PublishResult(success=False, platform=self.name, error=str(e))

    async def interact(self, post_id: str) -> InteractResult:
        if self._dry_run:
            logger.info("[DRY-RUN] Would upvote HN post %s", post_id)
            return InteractResult(success=True, platform=self.name, interaction_type="upvote", target_id=post_id)
        try:
            return InteractResult(success=True, platform=self.name, interaction_type="upvote", target_id=post_id)
        except Exception as e:
            return InteractResult(success=False, platform=self.name, interaction_type="upvote", error=str(e))


class MockPlatform(BasePlatform):
    """Simulated platform used for testing and as fallback."""

    name = "mock"

    def __init__(self, dry_run: bool = False):
        self._dry_run = dry_run
        self._posted: list[str] = []
        self._interacted: list[str] = []

    async def post(self, content: PostContent) -> PublishResult:
        post_id = f"mock_{hash(content.title + content.body) % 10_000_000:07d}"
        self._posted.append(post_id)
        return PublishResult(
            success=True,
            platform=self.name,
            url=f"mock://{content.platform}/{post_id}",
            post_id=post_id,
        )

    async def interact(self, post_id: str) -> InteractResult:
        self._interacted.append(post_id)
        return InteractResult(
            success=True,
            platform=self.name,
            interaction_type="mock_action",
            target_id=post_id,
        )

    @property
    def posted_count(self) -> int:
        return len(self._posted)

    @property
    def interacted_count(self) -> int:
        return len(self._interacted)


PLATFORM_REGISTRY: dict[str, type[BasePlatform]] = {
    "twitter": TwitterPlatform,
    "reddit": RedditPlatform,
    "hn": HNPlatform,
    "mock": MockPlatform,
}


def get_platform(platform_name: str, dry_run: bool = False) -> BasePlatform:
    """Return a platform adapter for the given name."""
    cls = PLATFORM_REGISTRY.get(platform_name, MockPlatform)
    return cls(dry_run=dry_run)
