"""
Payment Provider Abstraction
=============================

Abstract base class for payment providers + factory function.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .models import User


@dataclass
class OrderResult:
    success: bool = False
    order_id: str = ""
    provider_order_id: str = ""
    checkout_url: str = ""
    amount: float = 0.0
    currency: str = "usd"
    expires_at: str = ""
    error: str = ""
    raw: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "order_id": self.order_id,
            "provider_order_id": self.provider_order_id,
            "checkout_url": self.checkout_url,
            "amount": self.amount,
            "currency": self.currency,
            "expires_at": self.expires_at,
            "error": self.error,
        }


@dataclass
class CallbackResult:
    valid: bool = False
    provider_order_id: str = ""
    amount: float = 0.0
    currency: str = ""
    tier: str = ""
    event_type: str = ""
    raw: Any = None
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "provider_order_id": self.provider_order_id,
            "amount": self.amount,
            "currency": self.currency,
            "tier": self.tier,
            "event_type": self.event_type,
            "error": self.error,
        }


class PaymentProvider(ABC):
    @abstractmethod
    def create_order(
        self, user: User, tier: str, amount: float, currency: str
    ) -> OrderResult:
        raise NotImplementedError()

    @abstractmethod
    def verify_callback(self, payload: Any, headers: dict[str, str] | None = None) -> CallbackResult:
        raise NotImplementedError()

    @abstractmethod
    def refund(self, order_id: str, reason: str = "") -> bool:
        raise NotImplementedError()


def get_provider(channel: str) -> PaymentProvider:
    if channel == "stripe":
        from .stripe_adapter import StripeAdapter
        return StripeAdapter()
    if channel == "alipay":
        from .alipay_adapter import AlipayAdapter
        return AlipayAdapter()
    raise ValueError(f"Unknown payment channel: {channel}")
