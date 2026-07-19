"""
Polis-Hermes Autonomous Monetization Engine
==========================================

This module implements the agent-controlled monetization system where
AI autonomously decides when the system is ready to charge users.
"""

from .engine import MonetizationEngine
from .metrics import MetricsCollector
from .decision import DecisionEngine
from .config import MonetizationConfig

__version__ = "1.0.0"
__all__ = [
    "MonetizationEngine",
    "MetricsCollector",
    "DecisionEngine",
    "MonetizationConfig",
]

# Global engine instance
_engine: MonetizationEngine | None = None


def get_engine() -> MonetizationEngine:
    """Get the global monetization engine instance."""
    global _engine
    if _engine is None:
        _engine = MonetizationEngine()
    return _engine


def initialize(config: dict | None = None) -> MonetizationEngine:
    """Initialize the monetization system."""
    global _engine
    _engine = MonetizationEngine(config=config)
    return _engine


def status() -> dict:
    """Get current monetization status."""
    return get_engine().get_status()


def should_charge() -> bool:
    """Check if system should currently be charging."""
    return get_engine().should_charge()


def explain() -> str:
    """Get explanation of agent's monetization decision."""
    return get_engine().explain_decision()
