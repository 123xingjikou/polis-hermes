"""
Main Monetization Engine
=========================

Top-level engine that orchestrates all monetization activities.
"""

from datetime import datetime
import json

from .config import MonetizationConfig
from .decision import DecisionEngine, DecisionResult
from .metrics import MetricsCollector, AllMetrics


class MonetizationEngine:
    """Main engine for agent-controlled monetization."""

    def __init__(self, config=None):
        if isinstance(config, MonetizationConfig):
            self.config = config
        elif isinstance(config, dict):
            self.config = MonetizationConfig()
        else:
            self.config = MonetizationConfig()
        self.decision_engine = DecisionEngine(self.config)
        self.metrics_collector = MetricsCollector()
        self._start_time = datetime.utcnow()

    def get_status(self) -> dict:
        last_decision = self.decision_engine.get_last_decision()
        return {
            "system": {
                "version": "1.0.0",
                "uptime_since": self._start_time.isoformat(),
                "current_phase": self.config.phase,
                "agent_mode": self.config.agent_mode,
                "monetization_enabled": self.config.enabled,
            },
            "pricing": {
                "active_tiers": [t.to_dict() for t in self.config.get_active_tiers()],
                "paid_tiers": [t.to_dict() for t in self.config.get_paid_tiers()],
            },
            "last_decision": last_decision.to_dict() if last_decision else None,
            "config": self.config.to_dict(),
        }

    def should_charge(self) -> bool:
        if not self.config.enabled:
            return False
        if self.config.phase == "learning":
            return False
        if self.config.phase == "active":
            return len(self.config.get_paid_tiers()) > 0
        if self.config.phase == "paused":
            return False
        last = self.decision_engine.get_last_decision()
        if last and last.should_charge and last.confidence >= 0.70:
            self.config.phase = "active"
            self.config.activate_tier("professional")
            return True
        return False

    def evaluate(self) -> DecisionResult:
        return self.decision_engine.evaluate()

    def explain_decision(self) -> str:
        return self.decision_engine.explain()

    def activate_tier(self, tier_name: str) -> bool:
        valid = {"community", "professional", "enterprise", "sovereign"}
        if tier_name in valid:
            self.config.activate_tier(tier_name)
            return True
        return False

    def deactivate_tier(self, tier_name: str) -> bool:
        valid = {"community", "professional", "enterprise", "sovereign"}
        if tier_name in valid:
            self.config.deactivate_tier(tier_name)
            return True
        return False

    def update_pricing(self, tier_name: str, monthly: float, annual: float | None = None) -> bool:
        valid = {"community", "professional", "enterprise", "sovereign"}
        if tier_name in valid:
            self.config.update_price(tier_name, monthly, annual)
            return True
        return False

    def set_phase(self, phase: str) -> bool:
        if phase in {"learning", "evaluating", "active", "paused"}:
            self.config.phase = phase
            return True
        return False

    def get_metrics(self) -> AllMetrics:
        return self.metrics_collector.collect_all()

    def generate_report(self) -> str:
        status = self.get_status()
        lines = []
        lines.append("=" * 70)
        lines.append("POLIS-HERMES MONETIZATION ENGINE REPORT")
        lines.append("=" * 70)
        lines.append("")
        lines.append("SYSTEM STATUS")
        lines.append("-" * 40)
        lines.append(f"  Phase: {status['system']['current_phase'].upper()}")
        lines.append(f"  Agent Mode: {status['system']['agent_mode']}")
        lines.append(f"  Enabled: {status['system']['monetization_enabled']}")
        lines.append("")
        lines.append("PRICING TIERS")
        lines.append("-" * 40)
        for tier in status['pricing']['active_tiers']:
            price = "FREE" if tier['is_free'] else f"${tier['monthly_price']:.2f}/mo"
            lines.append(f"  {tier['display_name']}: {price}")
        lines.append("")
        if status['last_decision']:
            d = status['last_decision']
            lines.append("LAST DECISION")
            lines.append("-" * 40)
            lines.append(f"  Should Charge: {'YES' if d['should_charge'] else 'NO'}")
            lines.append(f"  Confidence: {d['confidence']:.1%}")
        lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Monetization Engine CLI")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("status", help="Show status")
    subparsers.add_parser("metrics", help="Show metrics")
    subparsers.add_parser("evaluate", help="Run evaluation")
    subparsers.add_parser("explain", help="Explain decision")
    subparsers.add_parser("report", help="Full report")
    activate_p = subparsers.add_parser("activate-tier")
    activate_p.add_argument("tier")
    price_p = subparsers.add_parser("update-price")
    price_p.add_argument("tier")
    price_p.add_argument("monthly", type=float)
    price_p.add_argument("annual", type=float, nargs="?")
    args = parser.parse_args()
    engine = MonetizationEngine()
    if args.command == "status":
        print(json.dumps(engine.get_status(), indent=2, default=str))
    elif args.command == "metrics":
        m = engine.get_metrics()
        print(json.dumps(m.to_dict(), indent=2, default=str))
    elif args.command == "evaluate":
        result = engine.evaluate()
        print(engine.explain_decision())
    elif args.command == "explain":
        print(engine.explain_decision())
    elif args.command == "report":
        print(engine.generate_report())
    elif args.command == "activate-tier":
        print(f"Activated: {engine.activate_tier(args.tier)}")
    elif args.command == "update-price":
        print(f"Updated: {engine.update_pricing(args.tier, args.monthly, args.annual)}")
    else:
        print(engine.generate_report())


if __name__ == "__main__":
    main()
