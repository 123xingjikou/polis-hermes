"""
Tests for PaymentOrchestrator.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from monetization.config import MonetizationConfig
from monetization.payment import _init_db
from monetization.payment.models import User, Order, Subscription, PendingEmail, PendingLicense
from monetization.payment.orchestrator import PaymentOrchestrator
from monetization.payment.provider import OrderResult, CallbackResult


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _init_db(path)
    yield path
    os.unlink(path)


@pytest.fixture
def config():
    cfg = MonetizationConfig()
    cfg.payment_enabled = True
    return cfg


@pytest.fixture
def orchestrator(config, temp_db_path):
    return PaymentOrchestrator(config=config, db_path=temp_db_path)


class TestPaymentOrchestratorCreateCheckout:
    def test_disabled_returns_error(self, temp_db_path):
        cfg = MonetizationConfig()
        cfg.payment_enabled = False
        orch = PaymentOrchestrator(config=cfg, db_path=temp_db_path)

        result = orch.create_checkout(
            user_id="", tier="professional", channel="stripe", email="a@b.com"
        )
        assert result.success is False
        assert "not enabled" in result.error

    def test_unknown_tier_returns_error(self, orchestrator):
        result = orchestrator.create_checkout(
            user_id="", tier="nonexistent", channel="stripe", email="a@b.com"
        )
        assert result.success is False
        assert "Unknown tier" in result.error

    def test_free_tier_returns_error(self, orchestrator):
        result = orchestrator.create_checkout(
            user_id="", tier="community", channel="stripe", email="a@b.com"
        )
        result = orchestrator.create_checkout(
            user_id="", tier="community", channel="stripe", email="a@b.com"
        )
        assert result.success is False

    def test_successful_checkout(self, orchestrator, temp_db_path):
        mock_provider = MagicMock()
        mock_provider.create_order.return_value = OrderResult(
            success=True,
            order_id="ord_test_123",
            provider_order_id="cs_test_123",
            checkout_url="https://checkout.stripe.com/pay/cs_test_123",
            amount=29.0,
            currency="usd",
        )

        with patch(
            "monetization.payment.orchestrator.get_provider",
            return_value=mock_provider,
        ):
            result = orchestrator.create_checkout(
                user_id="",
                tier="professional",
                channel="stripe",
                email="buyer@example.com",
            )

        assert result.success is True
        assert result.checkout_url == "https://checkout.stripe.com/pay/cs_test_123"

        user = User.get_by_email("buyer@example.com", temp_db_path)
        assert user is not None

    def test_creates_user_if_not_exists(self, orchestrator, temp_db_path):
        mock_provider = MagicMock()
        mock_provider.create_order.return_value = OrderResult(
            success=True,
            order_id="ord_123",
            provider_order_id="cs_123",
            checkout_url="https://example.com/pay",
            amount=29.0,
            currency="usd",
        )

        with patch(
            "monetization.payment.orchestrator.get_provider",
            return_value=mock_provider,
        ):
            orchestrator.create_checkout(
                user_id="",
                tier="professional",
                channel="stripe",
                email="newuser@example.com",
                name="New User",
            )

        user = User.get_by_email("newuser@example.com", temp_db_path)
        assert user is not None
        assert user.name == "New User"

    def test_uses_existing_user_by_id(self, orchestrator, temp_db_path):
        user = User(email="existing@example.com", name="Existing")
        user.save(temp_db_path)

        mock_provider = MagicMock()
        mock_provider.create_order.return_value = OrderResult(
            success=True,
            order_id="ord_exist",
            provider_order_id="cs_exist",
            checkout_url="https://example.com/pay",
            amount=29.0,
            currency="usd",
        )

        with patch(
            "monetization.payment.orchestrator.get_provider",
            return_value=mock_provider,
        ):
            orchestrator.create_checkout(
                user_id=user.id,
                tier="professional",
                channel="stripe",
                email="different@example.com",
            )

        loaded_user = User.get_by_id(user.id, temp_db_path)
        assert loaded_user is not None
        assert loaded_user.email == "existing@example.com"


class TestPaymentOrchestratorHandleWebhook:
    def test_invalid_callback(self, orchestrator):
        mock_provider = MagicMock()
        mock_provider.verify_callback.return_value = CallbackResult(
            valid=False, error="Bad signature"
        )

        with patch(
            "monetization.payment.orchestrator.get_provider",
            return_value=mock_provider,
        ):
            result = orchestrator.handle_webhook("stripe", b"{}", {})

        assert result["status"] == "error"
        assert "Bad signature" in result["message"]

    def test_non_payment_event_ignored(self, orchestrator):
        mock_provider = MagicMock()
        mock_provider.verify_callback.return_value = CallbackResult(
            valid=True,
            provider_order_id="cs_123",
            event_type="checkout.session.expired",
        )

        with patch(
            "monetization.payment.orchestrator.get_provider",
            return_value=mock_provider,
        ):
            result = orchestrator.handle_webhook("stripe", b"{}", {})

        assert result["status"] == "ok"
        assert "ignored" in result["message"]

    def test_order_not_found(self, orchestrator):
        mock_provider = MagicMock()
        mock_provider.verify_callback.return_value = CallbackResult(
            valid=True,
            provider_order_id="cs_nonexistent",
            event_type="checkout.session.completed",
            amount=29.0,
            currency="usd",
        )

        with patch(
            "monetization.payment.orchestrator.get_provider",
            return_value=mock_provider,
        ):
            result = orchestrator.handle_webhook("stripe", b"{}", {})

        assert result["status"] == "error"
        assert "not found" in result["message"]

    def test_idempotent_duplicate_payment(self, orchestrator, temp_db_path):
        user = User(email="dup@example.com")
        user.save(temp_db_path)

        order = Order(
            user_id=user.id,
            provider="stripe",
            channel="stripe",
            tier="professional",
            amount=29.0,
            currency="usd",
            provider_order_id="cs_dup",
        )
        order.mark_paid(temp_db_path)

        mock_provider = MagicMock()
        mock_provider.verify_callback.return_value = CallbackResult(
            valid=True,
            provider_order_id="cs_dup",
            event_type="checkout.session.completed",
            amount=29.0,
            currency="usd",
        )

        with patch(
            "monetization.payment.orchestrator.get_provider",
            return_value=mock_provider,
        ):
            result = orchestrator.handle_webhook("stripe", b"{}", {})

        assert result["status"] == "ok"
        assert "already paid" in result["message"]

    def test_amount_mismatch_rejected(self, orchestrator, temp_db_path):
        user = User(email="mismatch@example.com")
        user.save(temp_db_path)

        order = Order(
            user_id=user.id,
            provider="stripe",
            channel="stripe",
            tier="professional",
            amount=29.0,
            currency="usd",
            provider_order_id="cs_mismatch",
        )
        order.save(temp_db_path)

        mock_provider = MagicMock()
        mock_provider.verify_callback.return_value = CallbackResult(
            valid=True,
            provider_order_id="cs_mismatch",
            event_type="checkout.session.completed",
            amount=99.0,
            currency="usd",
        )

        with patch(
            "monetization.payment.orchestrator.get_provider",
            return_value=mock_provider,
        ):
            result = orchestrator.handle_webhook("stripe", b"{}", {})

        assert result["status"] == "error"
        assert "Amount mismatch" in result["message"]

    def test_successful_payment_processing(self, orchestrator, temp_db_path):
        user = User(email="success@example.com")
        user.save(temp_db_path)

        provider_order_id = "cs_success_123"
        order = Order(
            user_id=user.id,
            provider="stripe",
            channel="stripe",
            tier="professional",
            amount=29.0,
            currency="usd",
            provider_order_id=provider_order_id,
        )
        order.save(temp_db_path)

        mock_provider = MagicMock()
        mock_provider.verify_callback.return_value = CallbackResult(
            valid=True,
            provider_order_id=provider_order_id,
            event_type="checkout.session.completed",
            amount=29.0,
            currency="usd",
        )

        with patch(
            "monetization.payment.orchestrator.get_provider",
            return_value=mock_provider,
        ):
            with patch.object(orchestrator, "_issue_license_async"):
                with patch.object(orchestrator, "_queue_license_email_async"):
                    result = orchestrator.handle_webhook("stripe", b"{}", {})

        assert result["status"] == "ok"
        assert "processed" in result["message"]

        loaded_order = Order.get_by_id(order.id, temp_db_path)
        assert loaded_order.status == "paid"
        assert loaded_order.paid_at

    def test_subscription_created_on_payment(self, orchestrator, temp_db_path):
        user = User(email="sub@example.com")
        user.save(temp_db_path)

        provider_order_id = "cs_sub_123"
        order = Order(
            user_id=user.id,
            provider="stripe",
            channel="stripe",
            tier="professional",
            amount=29.0,
            currency="usd",
            provider_order_id=provider_order_id,
        )
        order.save(temp_db_path)

        mock_provider = MagicMock()
        mock_provider.verify_callback.return_value = CallbackResult(
            valid=True,
            provider_order_id=provider_order_id,
            event_type="checkout.session.completed",
            amount=29.0,
            currency="usd",
        )

        with patch(
            "monetization.payment.orchestrator.get_provider",
            return_value=mock_provider,
        ):
            with patch.object(orchestrator, "_issue_license_async"):
                with patch.object(orchestrator, "_queue_license_email_async"):
                    orchestrator.handle_webhook("stripe", b"{}", {})

        sub = Subscription.get_by_user(user.id, temp_db_path)
        assert sub is not None
        assert sub.tier == "professional"
        assert sub.status == "active"
        assert sub.expires_at


class TestPaymentOrchestratorQueries:
    def test_get_subscription(self, orchestrator, temp_db_path):
        user = User(email="query@example.com")
        user.save(temp_db_path)

        sub = Subscription(
            user_id=user.id,
            tier="professional",
            status="active",
        )
        sub.renew(days=30, db_path=temp_db_path)

        result = orchestrator.get_subscription(user.id)
        assert result is not None
        assert result["tier"] == "professional"
        assert result["status"] == "active"

    def test_get_subscription_none(self, orchestrator, temp_db_path):
        result = orchestrator.get_subscription("nonexistent")
        assert result is None

    def test_list_orders(self, orchestrator, temp_db_path):
        user = User(email="orders@example.com")
        user.save(temp_db_path)

        for i in range(3):
            order = Order(
                user_id=user.id,
                provider="stripe",
                channel="stripe",
                tier="professional",
                amount=29.0,
                currency="usd",
                provider_order_id=f"cs_orders_{i}",
            )
            order.save(temp_db_path)

        orders = orchestrator.list_orders(user.id)
        assert len(orders) == 3


class TestPaymentOrchestratorRetry:
    def test_retry_pending_emails(self, orchestrator, temp_db_path):
        pe = PendingEmail(
            user_email="retry@example.com",
            license_key="KEY-RETRY-123",
            tier="professional",
        )
        pe.save(temp_db_path)

        mock_mailer = MagicMock()
        mock_mailer.send_license_email.return_value = True
        orchestrator._mailer = mock_mailer

        count = orchestrator.retry_pending_emails()
        assert count == 1

        items = PendingEmail.list_all(temp_db_path)
        assert len(items) == 0

    def test_retry_pending_emails_failure(self, orchestrator, temp_db_path):
        pe = PendingEmail(
            user_email="fail@example.com",
            license_key="KEY-FAIL",
            tier="professional",
        )
        pe.save(temp_db_path)

        mock_mailer = MagicMock()
        mock_mailer.send_license_email.side_effect = Exception("SMTP error")
        orchestrator._mailer = mock_mailer

        count = orchestrator.retry_pending_emails()
        assert count == 0

        items = PendingEmail.list_all(temp_db_path)
        assert len(items) == 1
        assert items[0].attempts == 1

    def test_retry_pending_licenses(self, orchestrator, temp_db_path):
        user = User(email="license_retry@example.com")
        user.save(temp_db_path)

        pl = PendingLicense(
            user_id=user.id,
            tier="professional",
        )
        pl.save(temp_db_path)

        with patch.object(orchestrator, "_issue_license", return_value="LIC-KEY-123"):
            with patch.object(orchestrator, "_queue_license_email"):
                count = orchestrator.retry_pending_licenses()

        assert count == 1
        items = PendingLicense.list_all(temp_db_path)
        assert len(items) == 0

    def test_retry_pending_licenses_max_retries(self, orchestrator, temp_db_path):
        user = User(email="maxretry@example.com")
        user.save(temp_db_path)

        pl = PendingLicense(
            user_id=user.id,
            tier="professional",
            attempts=3,
        )
        pl.save(temp_db_path)

        count = orchestrator.retry_pending_licenses(max_retries=3)
        assert count == 0

        items = PendingLicense.list_all(temp_db_path)
        assert len(items) == 0
