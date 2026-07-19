"""
Payment Orchestrator
=====================

Core orchestrator that routes payment requests, manages subscriptions,
issues licenses, and triggers email delivery.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime, timedelta
from typing import Any

from ..config import MonetizationConfig
from . import get_db_connection, DEFAULT_DB_PATH
from .models import (
    User,
    Order,
    Subscription,
    PendingEmail,
    PendingLicense,
)
from .provider import (
    PaymentProvider,
    OrderResult,
    CallbackResult,
    get_provider,
)
from .mailer import Mailer


class PaymentOrchestrator:
    def __init__(
        self,
        config: MonetizationConfig | None = None,
        db_path: str = DEFAULT_DB_PATH,
    ):
        self._config = config or MonetizationConfig()
        self._db_path = db_path
        self._mailer = Mailer()

    def _resolve_price(self, tier: str, currency: str) -> float:
        tier_config = self._config.tiers.get(tier)
        if tier_config is None:
            raise ValueError(f"Unknown tier: {tier}")
        if tier_config.is_free:
            return 0.0
        price = tier_config.monthly_price
        if price < 0:
            raise ValueError(f"Tier {tier} requires custom pricing")
        return price

    def _get_or_create_user(
        self, user_id: str = "", email: str = "", name: str = ""
    ) -> User:
        if user_id:
            user = User.get_by_id(user_id, self._db_path)
            if user:
                return user
        if email:
            user = User.get_by_email(email, self._db_path)
            if user:
                return user
        user = User(email=email, name=name)
        user.save(self._db_path)
        return user

    def create_checkout(
        self,
        user_id: str,
        tier: str,
        channel: str,
        email: str = "",
        name: str = "",
        currency: str = "usd",
    ) -> OrderResult:
        if not self._config.payment_enabled:
            return OrderResult(success=False, error="Payment not enabled")

        try:
            amount = self._resolve_price(tier, currency)
        except ValueError as e:
            return OrderResult(success=False, error=str(e))

        if amount <= 0:
            return OrderResult(success=False, error=f"Tier {tier} is free, no checkout needed")

        user = self._get_or_create_user(user_id=user_id, email=email, name=name)

        provider = get_provider(channel)
        result = provider.create_order(user, tier, amount, currency)

        if result.success:
            self._after_checkout_created(result, user)

        return result

    def _after_checkout_created(self, result: OrderResult, user: User) -> None:
        pass

    def handle_webhook(
        self,
        channel: str,
        payload: Any,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        provider = get_provider(channel)
        callback = provider.verify_callback(payload, headers)

        if not callback.valid:
            return {"status": "error", "message": callback.error or "Invalid callback"}

        if not self._is_payment_event(callback.event_type):
            return {"status": "ok", "message": "Event ignored"}

        existing_order = Order.get_by_provider_order_id(
            callback.provider_order_id, self._db_path
        )

        if existing_order and existing_order.status == "paid":
            return {"status": "ok", "message": "Order already paid"}

        if existing_order is None:
            return {
                "status": "error",
                "message": f"Order not found: {callback.provider_order_id}",
            }

        user = User.get_by_id(existing_order.user_id, self._db_path)
        if user is None:
            return {"status": "error", "message": "User not found"}

        if callback.amount > 0 and abs(callback.amount - existing_order.amount) > 0.01:
            return {
                "status": "error",
                "message": (
                    f"Amount mismatch: expected {existing_order.amount}, "
                    f"got {callback.amount}"
                ),
            }

        existing_order.mark_paid(self._db_path)

        self._after_order_paid(existing_order, user)

        return {"status": "ok", "message": "Payment processed"}

    def _after_order_paid(self, order: Order, user: User) -> None:
        self._renew_subscription(order, user)
        self._issue_license_async(order, user)
        self._queue_license_email_async(order, user)

    def _is_payment_event(self, event_type: str) -> bool:
        if not event_type:
            return False
        paid_events = {
            "checkout.session.completed",
            "payment_intent.succeeded",
            "trade_status_sync",
            "TRADE_SUCCESS",
            "TRADE_FINISHED",
        }
        return event_type in paid_events

    def _renew_subscription(self, order: Order, user: User) -> None:
        sub = Subscription.get_by_user(user.id, self._db_path)
        if sub is None:
            sub = Subscription(
                user_id=user.id,
                tier=order.tier,
                status="active",
            )
            sub.renew(days=30, db_path=self._db_path)
        else:
            sub.tier = order.tier
            sub.renew(days=30, db_path=self._db_path)

    def _issue_license(self, order: Order, user: User) -> str | None:
        try:
            from security.license_mgr import LicenseManager
            lm = LicenseManager()
            lic_key = lm.issue(
                customer=user.email or user.id,
                tier=order.tier,
                days_valid=365,
            )
            return lic_key
        except Exception:
            pending = PendingLicense(
                user_id=user.id,
                tier=order.tier,
            )
            pending.save(self._db_path)
            return None

    def _issue_license_async(self, order: Order, user: User) -> None:
        thread = threading.Thread(
            target=self._issue_license,
            args=(order, user),
            daemon=True,
            name=f"issue-license-{order.id}",
        )
        thread.start()

    def _queue_license_email(
        self, order: Order, user: User, license_key: str
    ) -> None:
        if not user.email or not license_key:
            return
        try:
            self._mailer.send_license_email(
                user_email=user.email,
                license_key=license_key,
                tier=order.tier,
                expires_at="",
            )
        except Exception:
            pending = PendingEmail(
                user_email=user.email,
                license_key=license_key,
                tier=order.tier,
            )
            pending.save(self._db_path)

    def _queue_license_email_async(self, order: Order, user: User) -> None:
        thread = threading.Thread(
            target=self._issue_license_and_email,
            args=(order, user),
            daemon=True,
            name=f"queue-email-{order.id}",
        )
        thread.start()

    def _issue_license_and_email(self, order: Order, user: User) -> None:
        lic_key = self._issue_license(order, user)
        if lic_key:
            self._queue_license_email(order, user, lic_key)

    def get_subscription(self, user_id: str) -> dict[str, Any] | None:
        sub = Subscription.get_by_user(user_id, self._db_path)
        if sub is None:
            return None
        return sub.to_dict()

    def list_orders(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        orders = Order.list_by_user(user_id, limit=limit, db_path=self._db_path)
        return [o.to_dict() for o in orders]

    def retry_pending_emails(self, max_retries: int = 3) -> int:
        pending_list = PendingEmail.list_all(self._db_path)
        sent_count = 0
        for pending in pending_list:
            if pending.attempts >= max_retries:
                pending.delete(self._db_path)
                continue
            try:
                self._mailer.send_license_email(
                    user_email=pending.user_email,
                    license_key=pending.license_key,
                    tier=pending.tier,
                    expires_at="",
                )
                pending.delete(self._db_path)
                sent_count += 1
            except Exception:
                pending.increment_attempts(self._db_path)
        return sent_count

    def retry_pending_licenses(self, max_retries: int = 3) -> int:
        pending_list = PendingLicense.list_all(self._db_path)
        issued_count = 0
        for pending in pending_list:
            if pending.attempts >= max_retries:
                pending.delete(self._db_path)
                continue
            user = User.get_by_id(pending.user_id, self._db_path)
            if user is None:
                pending.delete(self._db_path)
                continue
            order = Order(user_id=user.id, tier=pending.tier, amount=0, currency="usd",
                          provider_order_id=f"retry-{pending.id}")
            lic_key = self._issue_license(order, user)
            if lic_key:
                self._queue_license_email(order, user, lic_key)
                pending.delete(self._db_path)
                issued_count += 1
            else:
                pending.increment_attempts(self._db_path)
        return issued_count
