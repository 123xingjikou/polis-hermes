"""
Tests for AlipayAdapter with mocked alipay SDK.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from monetization.payment import _init_db
from monetization.payment.models import User, Order
from monetization.payment.alipay_adapter import AlipayAdapter


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _init_db(path)
    yield path
    os.unlink(path)


@pytest.fixture
def mock_alipay_instance():
    mock = MagicMock()
    mock.api_alipay_trade_page_pay.return_value = (
        "app_id=2021xxx&biz_content=xxx&sign=abc123"
    )
    mock.verify.return_value = True
    mock.api_alipay_trade_refund.return_value = {
        "code": "10000",
        "msg": "Success",
    }
    return mock


@pytest.fixture
def mock_alipay_class(mock_alipay_instance):
    mock_cls = MagicMock()
    mock_cls.return_value = mock_alipay_instance
    return mock_cls


@pytest.fixture
def adapter(temp_db_path, mock_alipay_class):
    with patch.dict(os.environ, {
        "ALIPAY_APP_ID": "2021000000000000",
        "ALIPAY_PRIVATE_KEY": "fake_private_key",
        "ALIPAY_PUBLIC_KEY": "fake_public_key",
    }):
        with patch(
            "monetization.payment.alipay_adapter.AlipayAdapter._get_alipay_module",
            return_value=mock_alipay_class,
        ):
            yield AlipayAdapter(db_path=temp_db_path)


class TestAlipayAdapterCreateOrder:
    def test_create_order_success(self, adapter, mock_alipay_class, mock_alipay_instance, temp_db_path):
        user = User(email="buyer@example.com", name="Buyer")
        user.save(temp_db_path)

        with patch.object(adapter, "_get_alipay_module", return_value=mock_alipay_class):
            result = adapter.create_order(user, "professional", 29.0, "cny")

        assert result.success is True
        assert "openapi.alipay.com" in result.checkout_url
        assert result.amount == 29.0
        assert result.currency == "cny"
        assert result.order_id

    def test_create_order_without_credentials(self, temp_db_path):
        with patch.dict(os.environ, {
            "ALIPAY_APP_ID": "",
            "ALIPAY_PRIVATE_KEY": "",
        }):
            adapter = AlipayAdapter(db_path=temp_db_path)
            user = User(email="test@example.com")
            result = adapter.create_order(user, "professional", 29.0, "cny")

        assert result.success is False
        assert "not configured" in result.error

    def test_create_order_saves_to_db(self, adapter, mock_alipay_class, temp_db_path):
        user = User(email="save@example.com", name="Save")
        user.save(temp_db_path)

        with patch.object(adapter, "_get_alipay_module", return_value=mock_alipay_class):
            result = adapter.create_order(user, "professional", 29.0, "cny")

        order = Order.get_by_id(result.order_id, temp_db_path)
        assert order is not None
        assert order.provider == "alipay"
        assert order.status == "pending"

    def test_create_order_handles_exception(self, adapter, temp_db_path):
        mock_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.api_alipay_trade_page_pay.side_effect = Exception("API Error")
        mock_cls.return_value = mock_instance

        user = User(email="err@example.com")
        user.save(temp_db_path)

        with patch.object(adapter, "_get_alipay_module", return_value=mock_cls):
            result = adapter.create_order(user, "professional", 29.0, "cny")

        assert result.success is False
        assert "API Error" in result.error

    def test_module_import_error(self):
        with patch.dict(os.environ, {
            "ALIPAY_APP_ID": "app_id",
            "ALIPAY_PRIVATE_KEY": "key",
        }):
            adapter = AlipayAdapter()
            with patch.dict("sys.modules", {"alipay": None}):
                with patch("builtins.__import__", side_effect=ImportError):
                    with pytest.raises(RuntimeError, match="alipay-sdk-python not installed"):
                        adapter._get_alipay_module()


class TestAlipayAdapterVerifyCallback:
    def test_verify_valid_callback(self, adapter, mock_alipay_class, mock_alipay_instance):
        payload = {
            "out_trade_no": "ord_123",
            "trade_no": "202607190000000001",
            "trade_status": "TRADE_SUCCESS",
            "total_amount": "29.00",
            "buyer_logon_id": "buyer@example.com",
            "sign": "fake_sign",
            "sign_type": "RSA2",
        }

        with patch.object(adapter, "_get_alipay_module", return_value=mock_alipay_class):
            result = adapter.verify_callback(payload)

        assert result.valid is True
        assert result.provider_order_id == "202607190000000001"
        assert result.amount == 29.0
        assert result.currency == "cny"
        assert result.event_type == "TRADE_SUCCESS"

    def test_verify_trade_finished(self, adapter, mock_alipay_class, mock_alipay_instance):
        payload = {
            "out_trade_no": "ord_123",
            "trade_no": "202607190000000001",
            "trade_status": "TRADE_FINISHED",
            "total_amount": "29.00",
            "sign": "fake_sign",
            "sign_type": "RSA2",
        }

        with patch.object(adapter, "_get_alipay_module", return_value=mock_alipay_class):
            result = adapter.verify_callback(payload)

        assert result.valid is True
        assert result.event_type == "TRADE_SUCCESS"

    def test_verify_empty_payload(self, adapter):
        result = adapter.verify_callback(None)
        assert result.valid is False
        assert "Empty payload" in result.error

    def test_verify_missing_public_key(self, temp_db_path):
        with patch.dict(os.environ, {"ALIPAY_PUBLIC_KEY": ""}):
            adapter = AlipayAdapter(db_path=temp_db_path)
            result = adapter.verify_callback({"trade_status": "TRADE_SUCCESS"})

        assert result.valid is False
        assert "not configured" in result.error

    def test_verify_missing_sign(self, adapter, mock_alipay_class):
        payload = {
            "out_trade_no": "ord_123",
            "trade_status": "TRADE_SUCCESS",
        }

        with patch.object(adapter, "_get_alipay_module", return_value=mock_alipay_class):
            result = adapter.verify_callback(payload)

        assert result.valid is False
        assert "Missing sign" in result.error

    def test_verify_bad_signature(self, adapter, mock_alipay_class):
        instance = mock_alipay_class.return_value
        instance.verify.return_value = False
        payload = {
            "out_trade_no": "ord_123",
            "trade_status": "TRADE_SUCCESS",
            "sign": "bad_sign",
        }

        with patch.object(adapter, "_get_alipay_module", return_value=mock_alipay_class):
            result = adapter.verify_callback(payload)

        assert result.valid is False
        assert "Signature verification failed" in result.error

    def test_verify_bytes_payload(self, adapter, mock_alipay_class, mock_alipay_instance):
        payload = json.dumps({
            "out_trade_no": "ord_123",
            "trade_no": "202607190000000001",
            "trade_status": "TRADE_SUCCESS",
            "total_amount": "29.00",
            "sign": "fake_sign",
            "sign_type": "RSA2",
        }).encode("utf-8")

        with patch.object(adapter, "_get_alipay_module", return_value=mock_alipay_class):
            result = adapter.verify_callback(payload)

        assert result.valid is True

    def test_verify_string_payload(self, adapter, mock_alipay_class, mock_alipay_instance):
        payload = json.dumps({
            "out_trade_no": "ord_123",
            "trade_no": "202607190000000001",
            "trade_status": "TRADE_SUCCESS",
            "total_amount": "29.00",
            "sign": "fake_sign",
            "sign_type": "RSA2",
        })

        with patch.object(adapter, "_get_alipay_module", return_value=mock_alipay_class):
            result = adapter.verify_callback(payload)

        assert result.valid is True


class TestAlipayAdapterRefund:
    def test_refund_success(self, adapter, mock_alipay_class, mock_alipay_instance, temp_db_path):
        user = User(email="refund@example.com")
        user.save(temp_db_path)

        order = Order(
            user_id=user.id,
            provider="alipay",
            channel="alipay",
            tier="professional",
            amount=29.0,
            currency="cny",
            provider_order_id="alipay_ref_123",
        )
        order.save(temp_db_path)
        order.mark_paid(temp_db_path)

        with patch.object(adapter, "_get_alipay_module", return_value=mock_alipay_class):
            result = adapter.refund(order.id, "Customer request")

        assert result is True
        loaded = Order.get_by_id(order.id, temp_db_path)
        assert loaded.status == "refunded"

    def test_refund_order_not_found(self, adapter, temp_db_path):
        with patch.object(adapter, "_get_alipay_module", return_value=mock_alipay_class):
            result = adapter.refund("nonexistent")
        assert result is False

    def test_refund_failure(self, adapter, mock_alipay_class, temp_db_path):
        user = User(email="fail@example.com")
        user.save(temp_db_path)

        order = Order(
            user_id=user.id,
            provider="alipay",
            channel="alipay",
            tier="professional",
            amount=29.0,
            currency="cny",
            provider_order_id="alipay_fail",
        )
        order.mark_paid(temp_db_path)

        instance = mock_alipay_class.return_value
        instance.api_alipay_trade_refund.return_value = {
            "code": "40004",
            "msg": "Business Failed",
        }

        with patch.object(adapter, "_get_alipay_module", return_value=mock_alipay_class):
            result = adapter.refund(order.id)

        assert result is False

    def test_refund_without_credentials(self, temp_db_path):
        with patch.dict(os.environ, {
            "ALIPAY_APP_ID": "",
            "ALIPAY_PRIVATE_KEY": "",
        }):
            adapter = AlipayAdapter(db_path=temp_db_path)
            result = adapter.refund("any_id")
        assert result is False
