"""
Monetization Configuration
===========================

Defines the configuration structure for the monetization system.
"""

from dataclasses import dataclass, field
from typing import Literal
import os

TierName = Literal["community", "professional", "enterprise", "sovereign"]
AgentMode = Literal["autonomous", "advisory", "disabled"]


@dataclass
class PricingTier:
    """Represents a single pricing tier."""
    name: TierName
    display_name: str
    monthly_price: float
    annual_price: float
    features: list[str]
    is_active: bool = False
    is_free: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "monthly_price": self.monthly_price,
            "annual_price": self.annual_price,
            "features": self.features,
            "is_active": self.is_active,
            "is_free": self.is_free,
        }


@dataclass
class ThresholdConfig:
    """Metrics thresholds for charging decisions."""
    min_user_adoption_rate: float = 0.75
    min_system_stability: float = 0.99
    min_feature_completeness: float = 0.80
    min_user_engagement_score: float = 6.5
    min_revenue_potential: str = "medium"
    max_support_burden: str = "manageable"
    min_daily_active_users: int = 100
    min_monthly_recurring_revenue: float = 0

    def to_dict(self) -> dict:
        return {
            "min_user_adoption_rate": self.min_user_adoption_rate,
            "min_system_stability": self.min_system_stability,
            "min_feature_completeness": self.min_feature_completeness,
            "min_user_engagement_score": self.min_user_engagement_score,
            "min_revenue_potential": self.min_revenue_potential,
            "max_support_burden": self.max_support_burden,
            "min_daily_active_users": self.min_daily_active_users,
            "min_monthly_recurring_revenue": self.min_monthly_recurring_revenue,
        }


@dataclass
class MonetizationConfig:
    """Main configuration for the monetization system."""
    agent_mode: AgentMode = "autonomous"
    enabled: bool = True
    phase: Literal["learning", "evaluating", "active", "paused"] = "learning"

    tiers: dict[TierName, PricingTier] = field(default_factory=lambda: {
        "community": PricingTier(
            name="community",
            display_name="Community",
            monthly_price=0,
            annual_price=0,
            features=["Basic agent access", "Community support", "Limited API calls (100/day)"],
            is_active=True,
            is_free=True,
        ),
        "professional": PricingTier(
            name="professional",
            display_name="Professional",
            monthly_price=29,
            annual_price=290,
            features=["Full agent access", "Priority support", "Unlimited API calls"],
        ),
        "enterprise": PricingTier(
            name="enterprise",
            display_name="Enterprise",
            monthly_price=99,
            annual_price=990,
            features=["Everything in Professional", "SLA guarantees", "Dedicated infrastructure"],
        ),
        "sovereign": PricingTier(
            name="sovereign",
            display_name="Sovereign",
            monthly_price=-1,
            annual_price=-1,
            features=["Everything in Enterprise", "Self-hosted deployment", "Full source code access"],
        ),
    })

    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    database_url: str = "sqlite:///monetization.db"
    github_token: str = ""
    github_repo_owner: str = ""
    github_repo_name: str = ""
    notify_on_phase_change: bool = True
    notify_on_pricing_change: bool = True
    notification_channels: list[str] = field(default_factory=lambda: ["github_issue"])

    def __post_init__(self):
        """Load configuration from environment variables."""
        self.stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", self.stripe_secret_key)
        self.stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", self.stripe_publishable_key)
        self.paypal_client_id = os.getenv("PAYPAL_CLIENT_ID", self.paypal_client_id)
        self.paypal_client_secret = os.getenv("PAYPAL_CLIENT_SECRET", self.paypal_client_secret)
        self.database_url = os.getenv("DATABASE_URL", self.database_url)
        self.github_token = os.getenv("GITHUB_TOKEN", self.github_token)
        self.github_repo_owner = os.getenv("GITHUB_REPO_OWNER", self.github_repo_owner)
        self.github_repo_name = os.getenv("GITHUB_REPO_NAME", self.github_repo_name)
        mode = os.getenv("MONETIZATION_AGENT_MODE", self.agent_mode)
        if mode in ("autonomous", "advisory", "disabled"):
            self.agent_mode = mode
        enabled = os.getenv("MONETIZATION_ENABLED", str(self.enabled))
        self.enabled = enabled.lower() in ("true", "1", "yes")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "agent_mode": self.agent_mode,
            "enabled": self.enabled,
            "phase": self.phase,
            "tiers": {k: v.to_dict() for k, v in self.tiers.items()},
            "thresholds": self.thresholds.to_dict(),
            "stripe_configured": bool(self.stripe_secret_key),
            "paypal_configured": bool(self.paypal_client_id),
        }

    def get_active_tiers(self) -> list[PricingTier]:
        return [t for t in self.tiers.values() if t.is_active]

    def get_paid_tiers(self) -> list[PricingTier]:
        return [t for t in self.tiers.values() if t.is_active and not t.is_free]

    def activate_tier(self, tier_name: TierName) -> None:
        if tier_name in self.tiers:
            self.tiers[tier_name].is_active = True

    def deactivate_tier(self, tier_name: TierName) -> None:
        if tier_name in self.tiers:
            self.tiers[tier_name].is_active = False

    def update_price(self, tier_name: TierName, monthly: float, annual: float | None = None) -> None:
        if tier_name in self.tiers:
            self.tiers[tier_name].monthly_price = monthly
            self.tiers[tier_name].annual_price = annual or monthly * 10
