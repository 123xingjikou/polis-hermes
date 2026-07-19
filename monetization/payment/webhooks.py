"""
Webhook Handlers
=================

Signature verification + field mapping + dispatch to orchestrator.
"""

from __future__ import annotations

import json
import hmac
import hashlib
from typing import Any

from .orchestrator import PaymentOrchestrator
from .provider import get_provider, CallbackResult
from . import DEFAULT_DB_PATH


class StripeWebhookHandler:
    def __init__(
        self,
        orchestrator: PaymentOrchestrator | None = None,
        webhook_secret: str = "",
    ):
        self._orchestrator = orchestrator or PaymentOrchestrator(db_path=DEFAULT_DB_PATH)
        self._webhook_secret = webhook_secret

    def _get_stripe_module(self) -> Any:
        try:
            import stripe
            return stripe
        except ImportError:
            raise RuntimeError("stripe SDK not installed")

    def parse_event(self, payload: bytes, sig_header: str) -> dict[str, Any]:
        if not self._webhook_secret:
            return {"status": "error", "message": "Webhook secret not configured"}

        stripe = self._get_stripe_module()

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self._webhook_secret
            )
        except Exception as e:
            return {"status": "error", "message": f"Signature verification failed: {e}" }

        if isinstance(event, dict):
            event_type = event.get("type", "")
        else:
            event_type = getattr(event, "type", "")

        return {"status": "ok", "event_type": event_type, "event": event}

    def handle(self, payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
        sig_header = headers.get("Stripe-Signature", "")
        if not sig_header:
            return {"status": "error", "message": "Missing Stripe-Signature header"}

        result = self.parse_event(payload, sig_header)
        if result["status"] != "ok":
            return result

        return self._orchestrator.handle_webhook(
            channel="stripe",
            payload=payload,
            headers=headers,
        )


class AlipayWebhookHandler:
    def __init__(
        self,
        orchestrator: PaymentOrchestrator | None = None,
    ):
        self._orchestrator = orchestrator or PaymentOrchestrator(db_path=DEFAULT_DB_PATH)

    def parse_notification(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, bytes):
            try:
                data = json.loads(payload.decode("utf-8"))
            except Exception as e:
                return {"status": "error", "message": f"Invalid JSON: {e}"}
        elif isinstance(payload, str):
            try:
                data = json.loads(payload)
            except Exception as e:
                return {"status": "error", "message": f"Invalid JSON: {e}"}
        elif isinstance(payload, dict):
            data = payload
        else:
            return {"status": "error", "message": "Unsupported payload type"}

        if "trade_status" not in data:
            return {"status": "error", "message": "Missing trade_status field"}

        return {"status": "ok", "data": data}

    def handle(self, payload: Any, headers: dict[str, str] | None = None) -> dict[str, Any]:
        parsed = self.parse_notification(payload)
        if parsed["status"] != "ok":
            return parsed

        return self._orchestrator.handle_webhook(
            channel="alipay",
            payload=payload,
            headers=headers,
        )


def create_stripe_handler(
    webhook_secret: str = "",
    db_path: str = DEFAULT_DB_PATH,
) -> StripeWebhookHandler:
    import os
    secret = webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET", "")
    orchestrator = PaymentOrchestrator(db_path=db_path)
    return StripeWebhookHandler(orchestrator=orchestrator, webhook_secret=secret)


def create_alipay_handler(
    db_path: str = DEFAULT_DB_PATH,
) -> AlipayWebhookHandler:
    orchestrator = PaymentOrchestrator(db_path=db_path)
    return AlipayWebhookHandler(orchestrator=orchestrator)
