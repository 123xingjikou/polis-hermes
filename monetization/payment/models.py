"""
Payment Data Models
====================

User, Order, Subscription dataclasses with CRUD methods.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from . import get_db_connection, DEFAULT_DB_PATH


def _generate_id(prefix: str = "") -> str:
    uid = uuid.uuid4().hex
    return f"{prefix}{uid}" if prefix else uid


@dataclass
class User:
    id: str = ""
    github_id: str = ""
    email: str = ""
    name: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = _generate_id("usr_")
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def save(self, db_path: str = DEFAULT_DB_PATH) -> None:
        conn = get_db_connection(db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO users (id, github_id, email, name, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (self.id, self.github_id, self.email, self.name, self.created_at),
            )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def get_by_id(cls, user_id: str, db_path: str = DEFAULT_DB_PATH) -> User | None:
        conn = get_db_connection(db_path)
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return cls(**dict(row))

    @classmethod
    def get_by_email(cls, email: str, db_path: str = DEFAULT_DB_PATH) -> User | None:
        conn = get_db_connection(db_path)
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return cls(**dict(row))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "github_id": self.github_id,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at,
        }


@dataclass
class Order:
    id: str = ""
    user_id: str = ""
    provider: str = ""
    channel: str = ""
    tier: str = ""
    amount: float = 0.0
    currency: str = "usd"
    provider_order_id: str = ""
    status: str = "pending"
    created_at: str = ""
    paid_at: str = ""
    refunded_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = _generate_id("ord_")
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def save(self, db_path: str = DEFAULT_DB_PATH) -> None:
        conn = get_db_connection(db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO orders
                   (id, user_id, provider, channel, tier, amount, currency,
                    provider_order_id, status, created_at, paid_at, refunded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    self.id, self.user_id, self.provider, self.channel,
                    self.tier, self.amount, self.currency,
                    self.provider_order_id, self.status, self.created_at,
                    self.paid_at, self.refunded_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def get_by_id(cls, order_id: str, db_path: str = DEFAULT_DB_PATH) -> Order | None:
        conn = get_db_connection(db_path)
        try:
            row = conn.execute(
                "SELECT * FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return cls(**dict(row))

    @classmethod
    def get_by_provider_order_id(
        cls, provider_order_id: str, db_path: str = DEFAULT_DB_PATH
    ) -> Order | None:
        conn = get_db_connection(db_path)
        try:
            row = conn.execute(
                "SELECT * FROM orders WHERE provider_order_id = ?",
                (provider_order_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return cls(**dict(row))

    @classmethod
    def list_by_user(
        cls, user_id: str, limit: int = 50, db_path: str = DEFAULT_DB_PATH
    ) -> list[Order]:
        conn = get_db_connection(db_path)
        try:
            rows = conn.execute(
                """SELECT * FROM orders WHERE user_id = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (user_id, limit),
            ).fetchall()
        finally:
            conn.close()
        return [cls(**dict(row)) for row in rows]

    def mark_paid(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.status = "paid"
        self.paid_at = datetime.utcnow().isoformat()
        self.save(db_path)

    def mark_refunded(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.status = "refunded"
        self.refunded_at = datetime.utcnow().isoformat()
        self.save(db_path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "channel": self.channel,
            "tier": self.tier,
            "amount": self.amount,
            "currency": self.currency,
            "provider_order_id": self.provider_order_id,
            "status": self.status,
            "created_at": self.created_at,
            "paid_at": self.paid_at,
            "refunded_at": self.refunded_at,
        }


@dataclass
class Subscription:
    id: str = ""
    user_id: str = ""
    tier: str = ""
    status: str = "active"
    started_at: str = ""
    expires_at: str = ""
    provider_subscription_id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = _generate_id("sub_")
        if not self.started_at:
            self.started_at = datetime.utcnow().isoformat()

    def save(self, db_path: str = DEFAULT_DB_PATH) -> None:
        conn = get_db_connection(db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO subscriptions
                   (id, user_id, tier, status, started_at, expires_at,
                    provider_subscription_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    self.id, self.user_id, self.tier, self.status,
                    self.started_at, self.expires_at,
                    self.provider_subscription_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def get_by_user(
        cls, user_id: str, db_path: str = DEFAULT_DB_PATH
    ) -> Subscription | None:
        conn = get_db_connection(db_path)
        try:
            row = conn.execute(
                """SELECT * FROM subscriptions WHERE user_id = ?
                   ORDER BY started_at DESC LIMIT 1""",
                (user_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return cls(**dict(row))

    def renew(self, days: int = 30, db_path: str = DEFAULT_DB_PATH) -> None:
        now = datetime.utcnow()
        if self.expires_at:
            current_expiry = datetime.fromisoformat(self.expires_at)
            base = max(now, current_expiry)
        else:
            base = now
        self.expires_at = (base + timedelta(days=days)).isoformat()
        self.status = "active"
        self.save(db_path)

    def cancel(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.status = "cancelled"
        self.save(db_path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tier": self.tier,
            "status": self.status,
            "started_at": self.started_at,
            "expires_at": self.expires_at,
            "provider_subscription_id": self.provider_subscription_id,
        }


@dataclass
class PendingEmail:
    id: str = ""
    user_email: str = ""
    license_key: str = ""
    tier: str = ""
    attempts: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = _generate_id("pe_")
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def save(self, db_path: str = DEFAULT_DB_PATH) -> None:
        conn = get_db_connection(db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO pending_emails
                   (id, user_email, license_key, tier, attempts, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (self.id, self.user_email, self.license_key, self.tier,
                 self.attempts, self.created_at),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, db_path: str = DEFAULT_DB_PATH) -> None:
        conn = get_db_connection(db_path)
        try:
            conn.execute("DELETE FROM pending_emails WHERE id = ?", (self.id,))
            conn.commit()
        finally:
            conn.close()

    def increment_attempts(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.attempts += 1
        self.save(db_path)

    @classmethod
    def list_all(cls, db_path: str = DEFAULT_DB_PATH) -> list[PendingEmail]:
        conn = get_db_connection(db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM pending_emails ORDER BY created_at ASC"
            ).fetchall()
        finally:
            conn.close()
        return [cls(**dict(row)) for row in rows]


@dataclass
class PendingLicense:
    id: str = ""
    user_id: str = ""
    tier: str = ""
    attempts: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = _generate_id("pl_")
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def save(self, db_path: str = DEFAULT_DB_PATH) -> None:
        conn = get_db_connection(db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO pending_licenses
                   (id, user_id, tier, attempts, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (self.id, self.user_id, self.tier, self.attempts, self.created_at),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, db_path: str = DEFAULT_DB_PATH) -> None:
        conn = get_db_connection(db_path)
        try:
            conn.execute("DELETE FROM pending_licenses WHERE id = ?", (self.id,))
            conn.commit()
        finally:
            conn.close()

    def increment_attempts(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.attempts += 1
        self.save(db_path)

    @classmethod
    def list_all(cls, db_path: str = DEFAULT_DB_PATH) -> list[PendingLicense]:
        conn = get_db_connection(db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM pending_licenses ORDER BY created_at ASC"
            ).fetchall()
        finally:
            conn.close()
        return [cls(**dict(row)) for row in rows]
