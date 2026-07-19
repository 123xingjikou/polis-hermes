"""
Tests for StripeAdapter with mocked stripe SDK.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from monetization.payment import _init_db
from monetization.payment.models import User, Order
from monetization.payment.stripe_adapter import StripeAdapter


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _init_db(path)
    yield path
    os.unlink(path)


@pytest.fixture
def mock_stripe_module():
    mock = MagicMock()
    mock.checkout.Session.create.return_value = MagicMock(
        id="cs_test_abc123",
        url="https://checkout.stripe.com/pay/cs_test_abc123",
        expires_at=1700000000,
    )
    mock.Webhook.construct_event.return_value = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_abc123",
                "amount_total": 2900,
                "currency": "USD",
                "metadata": {"tier": "professional"},
            }
        },
    }
    return mock


@pytest.fixture
def adapter(temp_db_path, mock_stripe_module):
    with patch.dict(os.environ, {
        "STRIPE_SECRET_KEY": "sk_test_fake",
        "STRIPE_WEBHOOK_SECRET": "whsec_fake",
    }):
        with patch(
            "monetization.payment.stripe_adapter.StripeAdapter._get_stripe_module",
            return_value=mock_stripe_module,
        ):
            yield StripeAdapter(db_path=temp_db_path)


class TestStripeAdapterCreateOrder:
    def test_create_order_success(self, adapter, mock_stripe_module, temp_db_path):
        user = User(email="buyer@example.com", name="Buyer")
        user.save(temp_db_path)

        with patch.object(adapter, "_get_stripe_module", return_value=mock_stripe_module):
            result = adapter.create_order(user, "professional", 29.0, "usd")

        assert result.success is True
        assert result.checkout_url == "https://checkout.stripe.com/pay/cs_test_abc123"
        assert result.provider_order_id == "cs_test_abc123"
        assert result.amount == 29.0
        assert result.currency == "usd"
        assert result.order_id

    def test_create_order_without_secret_key(self, temp_db_path):
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": ""}):
            adapter = StripeAdapter(db_path=temp_db_path)
            user = User(email="test@example.com")
            result = adapter.create_order(user, "professional", 29.0, "usd")

        assert result.success is False
        assert "not configured" in result.error

    def test_create_order_saves_to_db(self, adapter, mock_stripe_module, temp_db_path):
        user = User(email="save@example.com", name="Save")
        user.save(temp_db_path)

        with patch.object(adapter, "_get_stripe_module", return_value=mock_stripe_module):
            result = adapter.create_order(user, "professional", 29.0, "usd")

        order = Order.get_by_id(result.order_id, temp_db_path)
        assert order is not None
        assert order.provider_order_id == "cs_test_abc123"
        assert order.status == "pending"

    def test_create_order_handles_exception(self, adapter, temp_db_path):
        mock = MagicMock()
        mock.checkout.Session.create.side_effect = Exception("API Error")

        user = User(email="err@example.com")
        user.save(temp_db_path)

        with patch.object(adapter, "_get_stripe_module", return_value=mock):
            result = adapter.create_order(user, "professional", 29.0, "usd")

        assert result.success is False
        assert "API Error" in result.error

    def test_module_import_error(self):
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_fake"}):
            adapter = StripeAdapter()
            with patch.dict("sys.modules", {"stripe": None}):
                with patch("builtins.__import__", side_effect=ImportError):
                    with pytest.raises(RuntimeError, match="stripe SDK not installed"):
                        adapter._get_stripe_module()


class TestStripeAdapterVerifyCallback:
    def test_verify_valid_callback(self, adapter, mock_stripe_module):
        payload = b'{"type": "checkout.session.completed"}'
        headers = {"Stripe-Signature": "t=123,v1=abc"}

        with patch.object(adapter, "_get_stripe_module", return_value=mock_stripe_module):
            result = adapter.verify_callback(payload, headers)

        assert result.valid is True
        assert result.provider_order_id == "cs_test_abc123"
        assert result.amount == 29.0
        assert result.currency == "usd"
        assert result.tier == "professional"
        assert result.event_type == "checkout.session.completed"

    def test_verify_missing_headers(self, adapter):
        result = adapter.verify_callback(b"{}", None)
        assert result.valid is False
        assert "Missing headers" in result.error

    def test_verify_missing_signature(self, adapter):
        result = adapter.verify_callback(b"{}", {"Other-Header": "value"})
        assert result.valid is False
        assert "Missing Stripe-Signature" in result.error

    def test_verify_missing_webhook_secret(self, temp_db_path):
        with patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": ""}):
            adapter = StripeAdapter(db_path=temp_db_path)
            result = adapter.verify_callback(b"{}", {"Stripe-Signature": "abc"})
        assert result.valid is False
        assert "not configured" in result.error

    def test_verify_bad_signature(self, adapter):
        mock = MagicMock()
        mock.Webhook.construct_event.side_effect = Exception("Bad sig")

        with patch.object(adapter, "_get_stripe_module", return_value=mock):
            result = adapter.verify_callback(
                b"{}", {"Stripe-Signature": "bad"}
            )

        assert result.valid is False
        assert "Signature verification failed" in result.error


class TestStripeAdapterRefund:
    def test_refund_success(self, adapter, temp_db_path):
        user = User(email="refund@example.com")
        user.save(temp_db_path)

        order = Order(
            user_id=user.id,
            provider="stripe",
            channel="stripe",
            tier="professional",
            amount=29.0,
            currency="usd",
            provider_order_id="pi_123",
        )
        order.save(temp_db_path)
        order.mark_paid(temp_db_path)

        mock = MagicMock()
        mock.Refund.create.return_value = {"id": "re_123"}

        with patch.object(adapter, "_get_stripe_module", return_value=mock):
            result = adapter.refund(order.id, "Customer request")

        assert result is True
        loaded = Order.get_by_id(order.id, temp_db_path)
        assert loaded.status == "refunded"

    def test_refund_order_not_found(self, adapter, temp_db_path):
        with patch.object(adapter, "_get_stripe_module", return_value=MagicMock()):
            result = adapter.refund("nonexistent")
        assert result is False

    def test_refund_failure(self, adapter, temp_db_path):
        user = User(email="fail@example.com")
        user.save(temp_db_path)

        order = Order(
            user_id=user.id,
            provider="stripe",
            channel="stripe",
            tier="professional",
            amount=29.0,
            currency="usd",
            provider_order_id="pi_fail",
        )
        order.mark_paid(temp_db_path)

        mock = MagicMock()
        mock.Refund.create.side_effect = Exception("Refund failed")

        with patch.object(adapter, "_get_stripe_module", return_value=mock):
            result = adapter.refund(order.id)

        assert result is False
