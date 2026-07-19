"""
Decision Engine
===============

The core AI decision-making component that autonomously determines:
1. WHEN to start charging (timing)
2. HOW MUCH to charge (pricing)
"""

from dataclasses import dataclass, field
from datetime import datetime
import math

from .config import MonetizationConfig
from .metrics import MetricsCollector, AllMetrics


@dataclass
class DecisionFactor:
    """A single factor in the decision process."""
    name: str
    weight: float
    score: float
    threshold: float
    reasoning: str = ""

    @property
    def is_passing(self) -> bool:
        return self.score >= self.threshold

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class DecisionResult:
    """Complete decision result with reasoning."""
    should_charge: bool
    confidence: float
    factors: list
    reasoning: str
    recommendations: list[str]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "should_charge": self.should_charge,
            "confidence": self.confidence,
            "factors": [f.__dict__ for f in self.factors],
            "reasoning": self.reasoning,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
        }


class DecisionEngine:
    """Engine that makes autonomous monetization decisions."""

    def __init__(self, config: MonetizationConfig):
        self.config = config
        self.metrics_collector = MetricsCollector()
        self._decision_history = []
        self._last_decision = None
        self._phase_start_time = datetime.utcnow()

    def evaluate(self, metrics: AllMetrics | None = None) -> DecisionResult:
        """Run a full evaluation and make a decision."""
        if metrics is None:
            metrics = self.metrics_collector.collect_all()

        factors = self._evaluate_factors(metrics)
        should_charge, confidence = self._make_decision(factors)
        reasoning = self._generate_reasoning(factors, should_charge, confidence)
        recommendations = self._generate_recommendations(factors, should_charge)

        result = DecisionResult(
            should_charge=should_charge,
            confidence=confidence,
            factors=factors,
            reasoning=reasoning,
            recommendations=recommendations,
        )

        self._decision_history.append(result)
        self._last_decision = result
        self._update_phase(result)
        return result

    def _evaluate_factors(self, metrics: AllMetrics) -> list:
        thresholds = self.config.thresholds
        feature_completeness = self.metrics_collector.get_feature_completeness()
        factors = []

        # User Adoption
        adoption_score = self._calculate_adoption(metrics)
        factors.append(DecisionFactor(
            name="User Adoption Rate",
            weight=0.20,
            score=adoption_score,
            threshold=thresholds.min_user_adoption_rate,
            reasoning=f"Adoption score: {adoption_score:.2f}"
        ))

        # System Stability
        stability_score = metrics.system.uptime_percentage * (1 - metrics.system.error_rate)
        factors.append(DecisionFactor(
            name="System Stability",
            weight=0.15,
            score=stability_score,
            threshold=thresholds.min_system_stability,
            reasoning=f"Uptime: {metrics.system.uptime_percentage:.2%}"
        ))

        # Feature Completeness
        factors.append(DecisionFactor(
            name="Feature Completeness",
            weight=0.15,
            score=feature_completeness,
            threshold=thresholds.min_feature_completeness,
            reasoning=f"Features: {feature_completeness:.1%} complete"
        ))

        # User Engagement
        engagement_score = self._calculate_engagement(metrics)
        factors.append(DecisionFactor(
            name="User Engagement",
            weight=0.15,
            score=engagement_score,
            threshold=thresholds.min_user_engagement_score / 10,
            reasoning=f"Satisfaction: {metrics.users.user_satisfaction_score}/10"
        ))

        # GitHub Popularity
        github_score = self._calculate_github_score(metrics)
        factors.append(DecisionFactor(
            name="Market Validation",
            weight=0.10,
            score=github_score,
            threshold=0.3,
            reasoning=f"Stars: {metrics.github.stars}, Forks: {metrics.github.forks}"
        ))

        # DAU
        dau_score = min(metrics.users.daily_active_users / thresholds.min_daily_active_users, 1.0)
        factors.append(DecisionFactor(
            name="Daily Active Users",
            weight=0.10,
            score=dau_score,
            threshold=1.0,
            reasoning=f"DAU: {metrics.users.daily_active_users}"
        ))

        # Support Burden
        support_score = 0.8
        factors.append(DecisionFactor(
            name="Support Scalability",
            weight=0.10,
            score=support_score,
            threshold=0.5,
            reasoning=f"Open tickets: {metrics.support.open_tickets}"
        ))

        # Financial Readiness
        has_stripe = bool(self.config.stripe_secret_key)
        financial_score = 0.5 if has_stripe else 0.0
        factors.append(DecisionFactor(
            name="Financial Readiness",
            weight=0.05,
            score=financial_score,
            threshold=0.0,
            reasoning=f"Stripe configured: {has_stripe}"
        ))

        return factors

    def _make_decision(self, factors: list) -> tuple:
        if not factors:
            return False, 0.0
        total_weight = sum(f.weight for f in factors)
        if total_weight == 0:
            return False, 0.0
        weighted_sum = sum(f.weighted_score for f in factors)
        overall_score = weighted_sum / total_weight
        passing_ratio = sum(1 for f in factors if f.is_passing) / len(factors)
        critical_passing = all(f.is_passing for f in factors if f.name in ["System Stability", "Feature Completeness"])
        confidence = overall_score * passing_ratio
        should_charge = (
            overall_score >= 0.70 and
            passing_ratio >= 0.75 and
            critical_passing and
            confidence >= 0.65
        )
        return should_charge, confidence

    def _calculate_adoption(self, metrics: AllMetrics) -> float:
        if metrics.users.total_users == 0:
            return 0.0
        score = (
            metrics.users.retention_rate_7d * 0.3 +
            metrics.users.retention_rate_30d * 0.5 +
            (1 - metrics.users.churn_rate) * 0.2
        )
        return max(0.0, min(1.0, score))

    def _calculate_engagement(self, metrics: AllMetrics) -> float:
        satisfaction_norm = metrics.users.user_satisfaction_score / 10
        nps_norm = (metrics.users.net_promoter_score + 100) / 200
        session_norm = min(metrics.users.average_session_duration_minutes / 60, 1.0)
        return satisfaction_norm * 0.5 + nps_norm * 0.3 + session_norm * 0.2

    def _calculate_github_score(self, metrics: AllMetrics) -> float:
        star_score = min(math.log10(max(metrics.github.stars, 1)) / 3, 1.0)
        fork_ratio = metrics.github.forks / max(metrics.github.stars, 1)
        fork_score = min(fork_ratio * 5, 1.0)
        return star_score * 0.6 + fork_score * 0.4

    def _generate_reasoning(self, factors, should_charge, confidence) -> str:
        passing = [f for f in factors if f.is_passing]
        failing = [f for f in factors if not f.is_passing]
        lines = []
        lines.append("=" * 60)
        lines.append("MONETIZATION DECISION REPORT")
        lines.append("=" * 60)
        lines.append(f"Decision: {'START CHARGING' if should_charge else 'DO NOT CHARGE'}")
        lines.append(f"Confidence: {confidence:.1%}")
        lines.append(f"Factors Passing: {len(passing)}/{len(factors)}")
        lines.append("")
        if passing:
            lines.append("PASSING FACTORS:")
            for f in passing:
                lines.append(f"  [PASS] {f.name}: {f.score:.2f} >= {f.threshold:.2f}")
        if failing:
            lines.append("FAILING FACTORS:")
            for f in failing:
                lines.append(f"  [FAIL] {f.name}: {f.score:.2f} < {f.threshold:.2f}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_recommendations(self, factors, should_charge) -> list:
        recommendations = []
        if should_charge:
            recommendations.append("Activate Professional pricing tier")
            recommendations.append("Enable payment processing")
            recommendations.append("Update landing page with pricing")
        for f in factors:
            if not f.is_passing:
                if f.name == "User Adoption Rate":
                    recommendations.append("Improve user onboarding")
                elif f.name == "System Stability":
                    recommendations.append("Invest in infrastructure")
                elif f.name == "Feature Completeness":
                    recommendations.append("Complete core features")
                elif f.name == "Daily Active Users":
                    recommendations.append("Grow user base")
        return recommendations

    def _update_phase(self, result) -> None:
        current = self.config.phase
        if current == "learning" and result.confidence > 0.3 and len(self._decision_history) >= 3:
            self.config.phase = "evaluating"
        elif current == "evaluating":
            if result.should_charge and result.confidence >= 0.7:
                self.config.phase = "active"
                self.config.activate_tier("professional")
                self.config.activate_tier("enterprise")
            elif result.confidence < 0.2:
                self.config.phase = "learning"
        elif current == "active" and result.confidence < 0.4:
            self.config.phase = "paused"
        elif current == "paused" and result.should_charge and result.confidence >= 0.6:
            self.config.phase = "active"

    def get_decision_history(self):
        return self._decision_history.copy()

    def get_last_decision(self):
        return self._last_decision

    def explain(self) -> str:
        if self._last_decision is None:
            return "No decision has been made yet."
        return self._last_decision.reasoning
