"""
Tests for payment data models (User, Order, Subscription).
"""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from monetization.payment import _init_db
from monetization.payment.models import (
    User,
    Order,
    Subscription,
    PendingEmail,
    PendingLicense,
    _generate_id,
)


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _init_db(path)
    yield path
    os.unlink(path)


class TestGenerateId:
    def test_generates_hex_id(self):
        uid = _generate_id()
        assert len(uid) == 32
        assert all(c in "0123456789abcdef" for c in uid)

    def test_generates_with_prefix(self):
        uid = _generate_id("usr_")
        assert uid.startswith("usr_")
        assert len(uid) == 36

    def test_unique_ids(self):
        ids = {_generate_id() for _ in range(100)}
        assert len(ids) == 100


class TestUser:
    def test_create_user(self, temp_db_path):
        user = User(email="test@example.com", name="Test User")
        assert user.id.startswith("usr_")
        assert user.email == "test@example.com"
        assert user.created_at

    def test_save_and_load(self, temp_db_path):
        user = User(email="save@example.com", name="Save Test")
        user.save(temp_db_path)

        loaded = User.get_by_id(user.id, temp_db_path)
        assert loaded is not None
        assert loaded.email == "save@example.com"
        assert loaded.name == "Save Test"

    def test_get_by_email(self, temp_db_path):
        user = User(email="find@example.com", name="Find Me")
        user.save(temp_db_path)

        found = User.get_by_email("find@example.com", temp_db_path)
        assert found is not None
        assert found.id == user.id

    def test_get_nonexistent(self, temp_db_path):
        assert User.get_by_id("nonexistent", temp_db_path) is None
        assert User.get_by_email("none@example.com", temp_db_path) is None

    def test_to_dict(self, temp_db_path):
        user = User(email="dict@example.com", name="Dict Test")
        d = user.to_dict()
        assert d["email"] == "dict@example.com"
        assert d["name"] == "Dict Test"
        assert "id" in d
        assert "created_at" in d


class TestOrder:
    def test_create_order(self, temp_db_path):
        user = User(email="order_test@example.com")
        user.save(temp_db_path)

        order = Order(
            user_id=user.id,
            provider="stripe",
            channel="stripe",
            tier="professional",
            amount=29.0,
            currency="usd",
            provider_order_id="cs_test_123",
        )
        assert order.id.startswith("ord_")
        assert order.status == "pending"

    def test_save_and_load(self, temp_db_path):
        user = User(email="save@example.com", name="Save Test")
        user.save(temp_db_path)

        order = Order(
            user_id=user.id,
            provider="stripe",
            channel="stripe",
            tier="professional",
            amount=29.0,
            currency="usd",
            provider_order_id="cs_test_save",
        )
        order.save(temp_db_path)

        loaded = Order.get_by_id(order.id, temp_db_path)
        assert loaded is not None
        assert loaded.provider_order_id == "cs_test_save"
        assert loaded.amount == 29.0

    def test_get_by_provider_order_id(self, temp_db_path):
        user = User(email="find_order@example.com")
        user.save(temp_db_path)

        order = Order(
            user_id=user.id,
            provider="stripe",
            channel="stripe",
            tier="professional",
            amount=29.0,
            currency="usd",
            provider_order_id="cs_unique_123",
        )
        order.save(temp_db_path)

        found = Order.get_by_provider_order_id("cs_unique_123", temp_db_path)
        assert found is not None
        assert found.id == order.id

    def test_mark_paid(self, temp_db_path):
        user = User(email="paid@example.com")
        user.save(temp_db_path)

        order = Order(
            user_id=user.id,
            provider="stripe",
            channel="stripe",
            tier="professional",
            amount=29.0,
            currency="usd",
            provider_order_id="cs_paid",
        )
        order.save(temp_db_path)
        order.mark_paid(temp_db_path)

        loaded = Order.get_by_id(order.id, temp_db_path)
        assert loaded.status == "paid"
        assert loaded.paid_at

    def test_mark_refunded(self, temp_db_path):
        user = User(email="refund@example.com")
        user.save(temp_db_path)

        order = Order(
            user_id=user.id,
            provider="stripe",
            channel="stripe",
            tier="professional",
            amount=29.0,
            currency="usd",
            provider_order_id="cs_ref",
        )
        order.mark_paid(temp_db_path)
        order.mark_refunded(temp_db_path)

        loaded = Order.get_by_id(order.id, temp_db_path)
        assert loaded.status == "refunded"
        assert loaded.refunded_at

    def test_list_by_user(self, temp_db_path):
        user = User(email="list@example.com")
        user.save(temp_db_path)

        for i in range(3):
            order = Order(
                user_id=user.id,
                provider="stripe",
                channel="stripe",
                tier="professional",
                amount=29.0,
                currency="usd",
                provider_order_id=f"cs_list_{i}",
            )
            order.save(temp_db_path)

        orders = Order.list_by_user(user.id, db_path=temp_db_path)
        assert len(orders) == 3

    def test_to_dict(self, temp_db_path):
        user = User(email="dict@example.com")
        user.save(temp_db_path)

        order = Order(
            user_id=user.id,
            provider="stripe",
            channel="stripe",
            tier="professional",
            amount=29.0,
            currency="usd",
            provider_order_id="cs_dict",
        )
        d = order.to_dict()
        assert d["amount"] == 29.0
        assert d["status"] == "pending"
        assert d["provider"] == "stripe"


class TestSubscription:
    def test_create_subscription(self, temp_db_path):
        user = User(email="sub_new@example.com")
        user.save(temp_db_path)

        sub = Subscription(
            user_id=user.id,
            tier="professional",
            status="active",
        )
        assert sub.id.startswith("sub_")
        assert sub.started_at

    def test_save_and_load(self, temp_db_path):
        user = User(email="usr_sub@example.com")
        user.save(temp_db_path)

        sub = Subscription(
            user_id=user.id,
            tier="professional",
            status="active",
        )
        sub.save(temp_db_path)

        loaded = Subscription.get_by_user(user.id, temp_db_path)
        assert loaded is not None
        assert loaded.tier == "professional"
        assert loaded.status == "active"

    def test_renew(self, temp_db_path):
        user = User(email="usr_renew@example.com")
        user.save(temp_db_path)

        sub = Subscription(
            user_id=user.id,
            tier="professional",
            status="active",
        )
        sub.save(temp_db_path)

        before = datetime.utcnow().isoformat()
        sub.renew(days=30, db_path=temp_db_path)

        loaded = Subscription.get_by_user(user.id, temp_db_path)
        assert loaded.expires_at
        assert loaded.status == "active"
        expiry = datetime.fromisoformat(loaded.expires_at)
        assert expiry > datetime.utcnow()

    def test_renew_extends_existing(self, temp_db_path):
        user = User(email="usr_extend@example.com")
        user.save(temp_db_path)

        future = (datetime.utcnow() + timedelta(days=10)).isoformat()
        sub = Subscription(
            user_id=user.id,
            tier="professional",
            status="active",
            expires_at=future,
        )
        sub.save(temp_db_path)
        sub.renew(days=30, db_path=temp_db_path)

        loaded = Subscription.get_by_user(user.id, temp_db_path)
        expiry = datetime.fromisoformat(loaded.expires_at)
        expected_min = datetime.utcnow() + timedelta(days=39)
        assert expiry >= expected_min

    def test_cancel(self, temp_db_path):
        user = User(email="usr_cancel@example.com")
        user.save(temp_db_path)

        sub = Subscription(
            user_id=user.id,
            tier="professional",
            status="active",
        )
        sub.save(temp_db_path)
        sub.cancel(temp_db_path)

        loaded = Subscription.get_by_user(user.id, temp_db_path)
        assert loaded.status == "cancelled"

    def test_to_dict(self, temp_db_path):
        user = User(email="usr_dict@example.com")
        user.save(temp_db_path)

        sub = Subscription(
            user_id=user.id,
            tier="professional",
            status="active",
        )
        d = sub.to_dict()
        assert d["tier"] == "professional"
        assert d["status"] == "active"


class TestPendingEmail:
    def test_create(self, temp_db_path):
        pe = PendingEmail(
            user_email="test@example.com",
            license_key="XXXXX-XXXXX-XXXXX-XXXXX",
            tier="professional",
        )
        assert pe.id.startswith("pe_")
        assert pe.attempts == 0

    def test_save_and_list(self, temp_db_path):
        pe = PendingEmail(
            user_email="list@example.com",
            license_key="KEY-123",
            tier="professional",
        )
        pe.save(temp_db_path)

        items = PendingEmail.list_all(temp_db_path)
        assert len(items) == 1
        assert items[0].user_email == "list@example.com"

    def test_increment_attempts(self, temp_db_path):
        pe = PendingEmail(
            user_email="inc@example.com",
            license_key="KEY-INC",
            tier="professional",
        )
        pe.save(temp_db_path)
        pe.increment_attempts(temp_db_path)
        pe.increment_attempts(temp_db_path)

        items = PendingEmail.list_all(temp_db_path)
        assert items[0].attempts == 2

    def test_delete(self, temp_db_path):
        pe = PendingEmail(
            user_email="del@example.com",
            license_key="KEY-DEL",
            tier="professional",
        )
        pe.save(temp_db_path)
        pe.delete(temp_db_path)

        items = PendingEmail.list_all(temp_db_path)
        assert len(items) == 0


class TestPendingLicense:
    def test_create(self, temp_db_path):
        user = User(email="pl_new@example.com")
        user.save(temp_db_path)

        pl = PendingLicense(
            user_id=user.id,
            tier="professional",
        )
        assert pl.id.startswith("pl_")
        assert pl.attempts == 0

    def test_save_and_list(self, temp_db_path):
        user = User(email="usr_pl@example.com")
        user.save(temp_db_path)

        pl = PendingLicense(
            user_id=user.id,
            tier="enterprise",
        )
        pl.save(temp_db_path)

        items = PendingLicense.list_all(temp_db_path)
        assert len(items) == 1
        assert items[0].tier == "enterprise"

    def test_increment_attempts(self, temp_db_path):
        user = User(email="usr_inc@example.com")
        user.save(temp_db_path)

        pl = PendingLicense(
            user_id=user.id,
            tier="professional",
        )
        pl.save(temp_db_path)
        pl.increment_attempts(temp_db_path)

        items = PendingLicense.list_all(temp_db_path)
        assert items[0].attempts == 1
