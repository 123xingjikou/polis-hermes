"""
Alipay Payment Adapter
=======================

Implements PaymentProvider for Alipay (domestic Chinese payments).
Uses alipay-sdk-python as optional dependency.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

from .models import User, Order, get_db_connection, DEFAULT_DB_PATH
from .provider import PaymentProvider, OrderResult, CallbackResult


class AlipayAdapter(PaymentProvider):
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self._db_path = db_path
        self._app_id = os.getenv("ALIPAY_APP_ID", "")
        self._private_key = os.getenv("ALIPAY_PRIVATE_KEY", "")
        self._public_key = os.getenv("ALIPAY_PUBLIC_KEY", "")
        self._gateway = os.getenv(
            "ALIPAY_GATEWAY", "https://openapi.alipay.com/gateway.do"
        )

    def _get_alipay_module(self) -> Any:
        try:
            from alipay import AliPay
            return AliPay
        except ImportError:
            raise RuntimeError(
                "alipay-sdk-python not installed: pip install alipay-sdk-python"
            )

    def _create_alipay_instance(self) -> Any:
        AliPay = self._get_alipay_module()
        return AliPay(
            appid=self._app_id,
            app_private_key_string=self._private_key,
            alipay_public_key_string=self._public_key,
            sign_type="RSA2",
        )

    def create_order(
        self, user: User, tier: str, amount: float, currency: str
    ) -> OrderResult:
        if not self._app_id or not self._private_key:
            return OrderResult(
                success=False, error="Alipay credentials not configured"
            )

        order = Order(
            user_id=user.id,
            provider="alipay",
            channel="alipay",
            tier=tier,
            amount=amount,
            currency=currency if currency else "cny",
        )

        provider_order_id = f"alipay_{uuid.uuid4().hex[:24]}"

        try:
            alipay = self._create_alipay_instance()

            order_string = alipay.api_alipay_trade_page_pay(
                out_trade_no=order.id,
                total_amount=str(amount),
                subject=f"Polis-Hermes {tier.title()}",
                return_url=os.getenv(
                    "ALIPAY_RETURN_URL",
                    "https://polis.example.com/payment/success",
                ),
                notify_url=os.getenv(
                    "ALIPAY_NOTIFY_URL",
                    "https://polis.example.com/api/v1/payments/alipay/notify",
                ),
            )

            order.provider_order_id = provider_order_id
            order.save(self._db_path)

            checkout_url = f"{self._gateway}?{order_string}"

            return OrderResult(
                success=True,
                order_id=order.id,
                provider_order_id=provider_order_id,
                checkout_url=checkout_url,
                amount=amount,
                currency=order.currency,
                expires_at=(datetime.utcnow() + timedelta(hours=1)).isoformat(),
                raw=order_string,
            )

        except Exception as e:
            return OrderResult(success=False, error=str(e))

    def verify_callback(self, payload: Any, headers: dict[str, str] | None = None) -> CallbackResult:
        if not payload:
            return CallbackResult(valid=False, error="Empty payload")

        if not self._public_key:
            return CallbackResult(valid=False, error="Alipay public key not configured")

        try:
            alipay = self._create_alipay_instance()

            if isinstance(payload, bytes):
                payload = json.loads(payload.decode("utf-8"))
            elif isinstance(payload, str):
                payload = json.loads(payload)

            sign = payload.pop("sign", "")
            sign_type = payload.pop("sign_type", "RSA2")

            if not sign:
                return CallbackResult(valid=False, error="Missing sign field")

            verified = alipay.verify(payload, sign)
            if not verified:
                return CallbackResult(valid=False, error="Signature verification failed")

            out_trade_no = payload.get("out_trade_no", "")
            trade_no = payload.get("trade_no", "")
            trade_status = payload.get("trade_status", "")
            total_amount = payload.get("total_amount", "0")
            buyer_email = payload.get("buyer_logon_id", "")

            event_type = "TRADE_SUCCESS" if trade_status in (
                "TRADE_SUCCESS", "TRADE_FINISHED"
            ) else trade_status

            amount = float(total_amount) if total_amount else 0.0

            return CallbackResult(
                valid=True,
                provider_order_id=trade_no or out_trade_no,
                amount=amount,
                currency="cny",
                tier="",
                event_type=event_type,
                raw=payload,
            )

        except Exception as e:
            return CallbackResult(valid=False, error=f"Callback processing error: {e}")

    def refund(self, order_id: str, reason: str = "") -> bool:
        if not self._app_id or not self._private_key:
            return False

        order = Order.get_by_id(order_id, self._db_path)
        if not order:
            return False

        try:
            alipay = self._create_alipay_instance()

            result = alipay.api_alipay_trade_refund(
                out_trade_no=order.id,
                refund_amount=str(order.amount),
                refund_reason=reason or "Customer request",
            )

            if result.get("code") == "10000":
                order.mark_refunded(self._db_path)
                return True
            return False

        except Exception:
            return False
