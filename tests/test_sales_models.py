"""
Tests for Sales Promotion Module
=================================

Tests models, credentials, templates, and analytics.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from monetization.sales.models import (
    PostContent,
    PublishResult,
    InteractResult,
    AnalyticsReport,
    DateRange,
)
from monetization.sales.credentials import (
    get_credentials,
    validate_credentials,
    mask_secret,
    CREDENTIAL_KEYS,
)
from monetization.sales.templates import (
    get_template,
    format_for_twitter,
    format_for_reddit,
    format_for_hn,
    CONTENT_TEMPLATES,
)
from monetization.sales.analytics import AnalyticsTracker
from monetization.sales.content_generator import ContentGenerator
from monetization.sales.platforms import MockPlatform, get_platform, BasePlatform


class TestPostContent:
    def test_create_basic(self):
        post = PostContent(
            platform="twitter",
            content_type="engagement",
            title="Test",
            body="Hello world",
        )
        assert post.platform == "twitter"
        assert post.content_type == "engagement"
        assert post.title == "Test"
        assert post.hashtags == []
        assert post.subreddit is None
        assert post.media_urls is None

    def test_create_with_all_fields(self):
        post = PostContent(
            platform="reddit",
            content_type="tutorial",
            title="Full Tutorial",
            body="Some body content",
            hashtags=["#Python", "#AI"],
            subreddit="learnpython",
            media_urls=["https://example.com/image.png"],
        )
        assert post.subreddit == "learnpython"
        assert len(post.hashtags) == 2
        assert len(post.media_urls) == 1

    def test_to_dict(self):
        post = PostContent(platform="hn", content_type="story", title="T", body="B")
        d = post.to_dict()
        assert d["platform"] == "hn"
        assert d["title"] == "T"
        assert isinstance(d, dict)


class TestPublishResult:
    def test_success_result(self):
        result = PublishResult(success=True, platform="twitter", url="https://x.com/123", post_id="abc")
        assert result.success is True
        assert result.platform == "twitter"
        assert result.error is None
        assert result.created_at

    def test_failure_result(self):
        result = PublishResult(success=False, platform="reddit", error="Auth failed")
        assert result.success is False
        assert result.error == "Auth failed"

    def test_to_dict(self):
        result = PublishResult(success=True, platform="hn")
        d = result.to_dict()
        assert d["success"] is True
        assert d["platform"] == "hn"


class TestInteractResult:
    def test_success(self):
        result = InteractResult(
            success=True,
            platform="twitter",
            interaction_type="like",
            target_id="tweet_123",
        )
        assert result.success is True
        assert result.interaction_type == "like"
        assert result.target_id == "tweet_123"

    def test_failure(self):
        result = InteractResult(
            success=False,
            platform="reddit",
            interaction_type="upvote",
            error="Network error",
        )
        assert result.success is False
        assert result.error == "Network error"

    def test_to_dict(self):
        result = InteractResult(success=True, platform="hn", interaction_type="upvote", target_id="hn_1")
        d = result.to_dict()
        assert d["success"] is True
        assert d["target_id"] == "hn_1"


class TestAnalyticsReport:
    def test_empty_report(self):
        report = AnalyticsReport()
        assert report.total_posts == 0
        assert report.success_rate == 0.0
        assert report.total_interactions == 0
        assert report.platform_breakdown == {}

    def test_filled_report(self):
        report = AnalyticsReport(
            total_posts=10,
            success_rate=0.9,
            total_interactions=25,
            platform_breakdown={"twitter": 5, "reddit": 3, "hn": 2},
            content_performance={"tutorial": {"total": 4, "success": 4}},
            date_range={"start": "2024-01-01", "end": "2024-01-31"},
        )
        assert report.total_posts == 10
        assert report.success_rate == 0.9

    def test_to_dict(self):
        report = AnalyticsReport(total_posts=5, success_rate=1.0)
        d = report.to_dict()
        assert d["total_posts"] == 5
        assert d["success_rate"] == 1.0


class TestDateRange:
    def test_create(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        dr = DateRange(start=start, end=end)
        assert dr.start == start
        assert dr.end == end

    def test_to_dict(self):
        dr = DateRange(start=datetime(2024, 1, 1), end=datetime(2024, 1, 31))
        d = dr.to_dict()
        assert "start" in d
        assert "end" in d
        assert "2024" in d["start"]


class TestCredentials:
    def test_get_credentials_empty(self):
        creds = get_credentials("nonexistent")
        assert creds == {}

    def test_get_credentials_structure(self):
        for platform, keys in CREDENTIAL_KEYS.items():
            for key in keys:
                assert isinstance(key, str)
                assert key.isupper() or "_" in key

    def test_validate_credentials_missing(self):
        assert validate_credentials("nonexistent") is False
        for platform in CREDENTIAL_KEYS:
            assert validate_credentials(platform) is False

    def test_validate_credentials_when_set(self, monkeypatch):
        monkeypatch.setenv("TWITTER_USERNAME", "user")
        monkeypatch.setenv("TWITTER_PASSWORD", "pass")
        monkeypatch.setenv("TWITTER_EMAIL", "u@e.com")
        assert validate_credentials("twitter") is True

    def test_mask_secret_empty(self):
        assert mask_secret("") == ""

    def test_mask_secret_short(self):
        assert mask_secret("abc") == "***"

    def test_mask_secret_long(self):
        masked = mask_secret("my-secret-password-1234")
        assert masked.endswith("1234")
        assert masked.startswith("*")
        assert len(masked) == len("my-secret-password-1234")


class TestTemplates:
    def test_get_template_tutorial(self):
        tutorials = get_template("tutorial")
        assert len(tutorials) > 0
        for t in tutorials:
            assert "{topic}" in t or "{topic_tag}" in t

    def test_get_template_story(self):
        stories = get_template("story")
        assert len(stories) > 0

    def test_get_template_engagement(self):
        engagements = get_template("engagement")
        assert len(engagements) > 0

    def test_get_template_unknown(self):
        assert get_template("nonexistent") == []

    def test_content_templates_structure(self):
        for ctype, templates in CONTENT_TEMPLATES.items():
            assert isinstance(ctype, str)
            assert isinstance(templates, list)
            assert len(templates) > 0

    def test_format_for_twitter_short(self):
        s = "short"
        assert format_for_twitter(s) == s

    def test_format_for_twitter_long(self):
        s = "x" * 300
        formatted = format_for_twitter(s)
        assert len(formatted) <= 280
        assert formatted.endswith("...")

    def test_format_for_reddit_unchanged(self):
        s = "any content"
        assert format_for_reddit(s) == s

    def test_format_for_hn_unchanged(self):
        s = "any content"
        assert format_for_hn(s) == s


class TestAnalyticsTracker:
    def test_init_creates_db(self, tmp_path):
        db_path = str(tmp_path / "test_analytics.db")
        tracker = AnalyticsTracker(db_path=db_path)
        assert os.path.exists(db_path)

    @pytest.mark.asyncio
    async def test_record_post(self, tmp_path):
        db_path = str(tmp_path / "test_analytics.db")
        tracker = AnalyticsTracker(db_path=db_path)
        content = PostContent(platform="twitter", content_type="engagement", title="T", body="B")
        result = PublishResult(success=True, platform="twitter", url="http://x.com/1")
        post_id = await tracker.record_post(content, result)
        assert post_id.startswith("post_")

    @pytest.mark.asyncio
    async def test_record_interaction(self, tmp_path):
        db_path = str(tmp_path / "test_analytics.db")
        tracker = AnalyticsTracker(db_path=db_path)
        iid = await tracker.record_interaction(
            interaction_type="like",
            target_id="tweet_123",
            status="success",
            platform="twitter",
        )
        assert iid.startswith("int_")

    @pytest.mark.asyncio
    async def test_generate_report_empty(self, tmp_path):
        db_path = str(tmp_path / "test_analytics.db")
        tracker = AnalyticsTracker(db_path=db_path)
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=30)
        report = await tracker.generate_report(DateRange(start=start, end=end))
        assert report.total_posts == 0
        assert report.success_rate == 0.0

    @pytest.mark.asyncio
    async def test_generate_report_with_data(self, tmp_path):
        db_path = str(tmp_path / "test_analytics.db")
        tracker = AnalyticsTracker(db_path=db_path)
        for i in range(3):
            content = PostContent(platform="twitter", content_type="engagement", title=f"T{i}", body=f"B{i}")
            result = PublishResult(success=True, platform="twitter")
            await tracker.record_post(content, result)
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=30)
        report = await tracker.generate_report(DateRange(start=start, end=end))
        assert report.total_posts == 3
        assert report.success_rate == 1.0
        assert report.platform_breakdown["twitter"] == 3

    @pytest.mark.asyncio
    async def test_generate_report_partial_success(self, tmp_path):
        db_path = str(tmp_path / "test_analytics.db")
        tracker = AnalyticsTracker(db_path=db_path)
        content = PostContent(platform="reddit", content_type="tutorial", title="T", body="B")
        await tracker.record_post(content, PublishResult(success=True, platform="reddit"))
        await tracker.record_post(content, PublishResult(success=False, platform="reddit", error="fail"))
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=30)
        report = await tracker.generate_report(DateRange(start=start, end=end))
        assert report.total_posts == 2
        assert report.success_rate == 0.5


class TestContentGenerator:
    def test_init_no_llm(self):
        gen = ContentGenerator(llm_capability=None)
        assert gen._llm is None

    @pytest.mark.asyncio
    async def test_generate_template_fallback(self):
        gen = ContentGenerator(llm_capability=None)
        content = await gen.generate("twitter", "story", "autonomous AI agents")
        assert isinstance(content, PostContent)
        assert content.platform == "twitter"
        assert content.content_type == "story"
        assert len(content.body) > 0

    @pytest.mark.asyncio
    async def test_generate_calendar(self):
        gen = ContentGenerator(llm_capability=None)
        calendar = await gen.generate_calendar(days=7)
        assert isinstance(calendar, list)
        assert len(calendar) > 0
        for content in calendar:
            assert isinstance(content, PostContent)

    @pytest.mark.asyncio
    async def test_generate_calendar_all_platforms(self):
        gen = ContentGenerator(llm_capability=None)
        calendar = await gen.generate_calendar(days=14)
        platforms = {c.platform for c in calendar}
        assert "twitter" in platforms
        assert "reddit" in platforms
        assert "hn" in platforms


class TestMockPlatform:
    def test_init(self):
        platform = MockPlatform(dry_run=True)
        assert platform.name == "mock"
        assert platform.posted_count == 0
        assert platform.interacted_count == 0

    @pytest.mark.asyncio
    async def test_post(self):
        platform = MockPlatform()
        content = PostContent(platform="mock", content_type="test", title="T", body="B")
        result = await platform.post(content)
        assert result.success is True
        assert result.platform == "mock"
        assert platform.posted_count == 1

    @pytest.mark.asyncio
    async def test_interact(self):
        platform = MockPlatform()
        result = await platform.interact("post_123")
        assert result.success is True
        assert result.target_id == "post_123"
        assert platform.interacted_count == 1

    @pytest.mark.asyncio
    async def test_multiple_posts(self):
        platform = MockPlatform()
        for i in range(5):
            content = PostContent(platform="mock", content_type="test", title=f"T{i}", body=f"B{i}")
            await platform.post(content)
        assert platform.posted_count == 5


class TestGetPlatform:
    def test_returns_mock_for_unknown(self):
        platform = get_platform("nonexistent")
        assert isinstance(platform, MockPlatform)

    def test_returns_twitter(self):
        platform = get_platform("twitter")
        assert platform.name == "twitter"

    def test_returns_reddit(self):
        platform = get_platform("reddit")
        assert platform.name == "reddit"

    def test_returns_hn(self):
        platform = get_platform("hn")
        assert platform.name == "hn"
