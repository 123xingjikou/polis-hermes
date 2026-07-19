"""
Mailer Module
==============

SMTP email delivery for license keys. Supports synchronous (aiosmtplib)
and fallback synchronous SMTP.
"""

from __future__ import annotations

import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any


class Mailer:
    def __init__(
        self,
        host: str = "",
        port: int = 0,
        user: str = "",
        password: str = "",
        sender: str = "",
        use_tls: bool = True,
    ):
        self._host = host or os.getenv("SMTP_HOST", "")
        self._port = port or int(os.getenv("SMTP_PORT", "587"))
        self._user = user or os.getenv("SMTP_USER", "")
        self._password = password or os.getenv("SMTP_PASSWORD", "")
        self._sender = sender or os.getenv("SMTP_FROM", "")
        self._use_tls = use_tls

    def _is_configured(self) -> bool:
        return bool(self._host and self._user and self._password)

    def send_license_email(
        self,
        user_email: str,
        license_key: str,
        tier: str,
        expires_at: str = "",
    ) -> bool:
        if not self._is_configured():
            raise RuntimeError("SMTP not configured")

        subject = f"Your Polis-Hermes {tier.title()} License Key"
        body = self._build_email_body(license_key, tier, expires_at)

        return self._send_email(user_email, subject, body)

    def _build_email_body(
        self, license_key: str, tier: str, expires_at: str
    ) -> str:
        lines = [
            "Thank you for purchasing Polis-Hermes!",
            "",
            f"Tier: {tier.title()}",
            f"License Key: {license_key}",
        ]
        if expires_at:
            lines.append(f"Expires: {expires_at}")
        lines.extend([
            "",
            "To activate your license, run:",
            f"  polis activate --key {license_key}",
            "",
            "If you need support, contact support@polis.example.com",
            "",
            "---",
            "Polis-Hermes Team",
        ])
        return "\n".join(lines)

    def _send_email(self, to: str, subject: str, body: str) -> bool:
        msg = MIMEMultipart()
        msg["From"] = self._sender or self._user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            with smtplib.SMTP(self._host, self._port, timeout=30) as server:
                if self._use_tls:
                    server.starttls()
                server.login(self._user, self._password)
                server.send_message(msg)
            return True
        except Exception:
            return False

    def send_async(
        self,
        user_email: str,
        license_key: str,
        tier: str,
        expires_at: str = "",
    ) -> None:
        thread = threading.Thread(
            target=self.send_license_email,
            args=(user_email, license_key, tier, expires_at),
            daemon=True,
            name=f"mailer-{user_email}",
        )
        thread.start()
