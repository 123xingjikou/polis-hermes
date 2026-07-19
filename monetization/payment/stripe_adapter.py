"""
Stripe Payment Adapter
=======================

Implements PaymentProvider for Stripe (international credit card payments).
Uses stripe Python SDK as optional dependency.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
from typing import Any

from .models import User, Order, get_db_connection, DEFAULT_DB_PATH
from .provider import PaymentProvider, OrderResult, CallbackResult


class StripeAdapter(PaymentProvider):
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self._db_path = db_path
        self._secret_key = os.getenv("STRIPE_SECRET_KEY", "")
        self._webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    def _get_stripe_module(self) -> Any:
        try:
            import stripe
            return stripe
        except ImportError:
            raise RuntimeError("stripe SDK not installed: pip install stripe")

    def create_order(
        self, user: User, tier: str, amount: float, currency: str
    ) -> OrderResult:
        if not self._secret_key:
            return OrderResult(success=False, error="Stripe secret key not configured")

        stripe = self._get_stripe_module()

        stripe.api_key = self._secret_key

        order = Order(
            user_id=user.id,
            provider="stripe",
            channel="stripe",
            tier=tier,
            amount=amount,
            currency=currency,
        )

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": currency,
                        "product_data": {"name": f"Polis-Hermes {tier.title()}"},
                        "unit_amount": int(amount * 100),
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=os.getenv(
                    "STRIPE_SUCCESS_URL",
                    "https://polis.example.com/payment/success",
                ),
                cancel_url=os.getenv(
                    "STRIPE_CANCEL_URL",
                    "https://polis.example.com/payment/cancel",
                ),
                customer_email=user.email,
                metadata={
                    "order_id": order.id,
                    "user_id": user.id,
                    "tier": tier,
                },
            )

            order.provider_order_id = checkout_session.id
            order.save(self._db_path)

            expires_at = ""
            if hasattr(checkout_session, "expires_at") and checkout_session.expires_at:
                expires_at = datetime.fromtimestamp(
                    checkout_session.expires_at
                ).isoformat()

            return OrderResult(
                success=True,
                order_id=order.id,
                provider_order_id=checkout_session.id,
                checkout_url=checkout_session.url or "",
                amount=amount,
                currency=currency,
                expires_at=expires_at,
                raw=checkout_session,
            )

        except Exception as e:
            return OrderResult(success=False, error=str(e))

    def verify_callback(self, payload: Any, headers: dict[str, str] | None = None) -> CallbackResult:
        if not headers:
            return CallbackResult(valid=False, error="Missing headers")

        sig_header = headers.get("Stripe-Signature", "")
        if not sig_header:
            return CallbackResult(valid=False, error="Missing Stripe-Signature header")

        if not self._webhook_secret:
            return CallbackResult(valid=False, error="Webhook secret not configured")

        stripe = self._get_stripe_module()

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self._webhook_secret
            )
        except Exception as e:
            return CallbackResult(valid=False, error=f"Signature verification failed: {e}")

        event_type = event.get("type", "") if isinstance(event, dict) else getattr(event, "type", "")
        data = event.get("data", {}) if isinstance(event, dict) else getattr(event, "data", {})
        obj = data.get("object", {}) if isinstance(data, dict) else getattr(data, "object", {})

        provider_order_id = obj.get("id", "") if isinstance(obj, dict) else getattr(obj, "id", "")
        metadata = obj.get("metadata", {}) if isinstance(obj, dict) else getattr(obj, "metadata", {})

        amount = 0.0
        amount_total = obj.get("amount_total", 0) if isinstance(obj, dict) else getattr(obj, "amount_total", 0)
        if amount_total:
            amount = amount_total / 100.0

        currency = obj.get("currency", "usd") if isinstance(obj, dict) else getattr(obj, "currency", "usd")
        if currency:
            currency = currency.lower()

        tier = metadata.get("tier", "") if isinstance(metadata, dict) else ""

        return CallbackResult(
            valid=True,
            provider_order_id=provider_order_id,
            amount=amount,
            currency=currency,
            tier=tier,
            event_type=event_type,
            raw=event,
        )

    def refund(self, order_id: str, reason: str = "") -> bool:
        stripe = self._get_stripe_module()
        if not self._secret_key:
            return False
        stripe.api_key = self._secret_key

        order = Order.get_by_id(order_id, self._db_path)
        if not order:
            return False

        try:
            payment_intents = stripe.PaymentIntent.list(
                limit=1,
            )
            refunds = stripe.Refund.create(
                payment_intent=order.provider_order_id,
                reason="requested_by_customer" if reason else None,
            )
            order.mark_refunded(self._db_path)
            return True
        except Exception:
            return False
