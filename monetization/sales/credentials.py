"""
Credentials Management
======================

Secure credential loading and validation from environment variables.
"""

from __future__ import annotations

import os

CREDENTIAL_KEYS: dict[str, list[str]] = {
    "twitter": [
        "TWITTER_USERNAME",
        "TWITTER_PASSWORD",
        "TWITTER_EMAIL",
    ],
    "reddit": [
        "REDDIT_USERNAME",
        "REDDIT_PASSWORD",
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
    ],
    "hn": [
        "HN_USERNAME",
        "HN_PASSWORD",
    ],
}


def get_credentials(platform: str) -> dict[str, str]:
    """Read platform credentials from environment variables."""
    env_keys = CREDENTIAL_KEYS.get(platform, [])
    return {key: os.getenv(key, "") for key in env_keys}


def validate_credentials(platform: str) -> bool:
    """Check if all required credentials are configured for the platform."""
    env_keys = CREDENTIAL_KEYS.get(platform, [])
    if not env_keys:
        return False
    return all(os.getenv(key, "") for key in env_keys)


def mask_secret(secret: str) -> str:
    """Mask a secret for safe logging (show only last 4 chars if long enough)."""
    if not secret:
        return ""
    if len(secret) <= 4:
        return "*" * len(secret)
    visible = secret[-4:]
    masked = "*" * (len(secret) - 4)
    return f"{masked}{visible}"
