"""
Sales Promotion Module
======================

Social media promotion agent for Polis-Hermes project.
Reaches audiences across Twitter/X, Reddit, and Hacker News.
"""

from .agent import SalesAgent, create_sales_agent, PROMOTER_PERSONALITY, PROMOTER_SKILLS
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
from .credentials import get_credentials, validate_credentials, mask_secret
from .templates import get_template, format_for_twitter, format_for_reddit, format_for_hn

__version__ = "0.1.0"

__all__ = [
    "SalesAgent",
    "create_sales_agent",
    "PROMOTER_PERSONALITY",
    "PROMOTER_SKILLS",
    "ContentGenerator",
    "SocialPublisher",
    "AnalyticsTracker",
    "PostContent",
    "PublishResult",
    "InteractResult",
    "AnalyticsReport",
    "DateRange",
    "get_credentials",
    "validate_credentials",
    "mask_secret",
    "get_template",
    "format_for_twitter",
    "format_for_reddit",
    "format_for_hn",
]
