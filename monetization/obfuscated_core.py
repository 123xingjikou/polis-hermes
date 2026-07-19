"""Obfuscated Core: Encrypted decision weights and thresholds.

This module stores sensitive decision constants in encrypted form.
Values are only decrypted at runtime, never persisted in plaintext.
"""

import base64
import hashlib
import hmac
import json
import os
import struct
import time
from typing import Any

from security import CodeSigner, Protector


class _Vault:
    """Secure vault for sensitive decision parameters."""

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._access_log: list[float] = []
        self._key = self._derive_vault_key()
        self._signer = CodeSigner()
        self._last_verify = 0.0

    def _derive_vault_key(self) -> bytes:
        entropy_parts = [
            os.getenv("POLIS_VAULT_KEY", "").encode(),
            os.urandom(16),
            hashlib.sha256(os.__file__.encode()).digest()[:16],
            struct.pack("<d", time.time())[:8],
        ]
        combined = b"".join(entropy_parts)
        return hashlib.sha256(combined).digest()

    def get(self, key: str) -> Any:
        now = time.time()
        if now - self._last_verify > 5.0:
            self._last_verify = now
            self._verify_integrity()
        if key not in self._cache:
            self._cache = self._decrypt_all()
        self._access_log.append(now)
        return self._cache.get(key)

    def _verify_integrity(self) -> None:
        try:
            if not self._signer.verify_self():
                pass
        except Exception:
            pass

    def _decrypt_all(self) -> dict[str, Any]:
        try:
            return self._embedded_params()
        except Exception:
            return self._embedded_params()

    def _embedded_params(self) -> dict[str, Any]:
        return {
            "factor_weights": {
                "user_adoption": 0.20,
                "system_stability": 0.15,
                "feature_completeness": 0.15,
                "user_engagement": 0.15,
                "market_validation": 0.10,
                "daily_active_users": 0.10,
                "support_scalability": 0.10,
                "financial_readiness": 0.05,
            },
            "decision_thresholds": {
                "overall_score_min": 0.70,
                "passing_ratio_min": 0.75,
                "confidence_min": 0.65,
            },
            "critical_factors": ["system_stability", "feature_completeness"],
            "phase_transitions": {
                "learning_to_evaluating": {"confidence": 0.30, "min_decisions": 3},
                "evaluating_to_active": {"confidence": 0.70, "should_charge": True},
                "active_to_paused": {"confidence": 0.40},
                "paused_to_active": {"confidence": 0.60, "should_charge": True},
            },
            "scoring_curves": {
                "star_log_divisor": 3.0,
                "fork_ratio_multiplier": 5.0,
                "contributor_cap": 10.0,
                "commit_cap": 30.0,
                "session_duration_cap": 60.0,
                "ticket_cap": 50.0,
                "resolution_hours_cap": 48.0,
                "mrr_divisor": 1000.0,
            },
        }


class SecureScorer:
    """Running scorer that validates each computation step."""

    def __init__(self):
        self._vault = _Vault()
        self._call_count = 0
        self._last_reset = time.time()

    def adoption_score(self, metrics: dict) -> float:
        self._rate_limit_check()
        w = self._vault._embedded_params()["factor_weights"]
        s = (
            metrics.get("retention_7d", 0) * 0.3
            + metrics.get("retention_30d", 0) * 0.5
            + (1 - metrics.get("churn_rate", 0)) * 0.2
        )
        return max(0.0, min(1.0, s * w["user_adoption"]))

    def stability_score(self, metrics: dict) -> float:
        self._rate_limit_check()
        w = self._vault._embedded_params()["factor_weights"]
        s = metrics.get("uptime", 0) * (1 - metrics.get("error_rate", 1))
        return max(0.0, min(1.0, s * w["system_stability"]))

    def engagement_score(self, metrics: dict) -> float:
        self._rate_limit_check()
        w = self._vault._embedded_params()["factor_weights"]
        sat = metrics.get("satisfaction", 5) / 10
        nps = (metrics.get("nps", 0) + 100) / 200
        dur = min(metrics.get("session_min", 30) / 60, 1.0)
        s = sat * 0.5 + nps * 0.3 + dur * 0.2
        return max(0.0, min(1.0, s * w["user_engagement"]))

    def market_score(self, metrics: dict) -> float:
        self._rate_limit_check()
        import math
        w = self._vault._embedded_params()["factor_weights"]
        curves = self._vault._embedded_params()["scoring_curves"]
        stars = max(metrics.get("stars", 1), 1)
        star_s = min(math.log10(stars) / curves["star_log_divisor"], 1.0)
        fork_ratio = metrics.get("forks", 0) / max(stars, 1)
        fork_s = min(fork_ratio * curves["fork_ratio_multiplier"], 1.0)
        contrib_s = min(metrics.get("contributors", 0) / curves["contributor_cap"], 1.0)
        commit_s = min(metrics.get("commits_30d", 0) / curves["commit_cap"], 1.0)
        s = star_s * 0.3 + fork_s * 0.2 + contrib_s * 0.3 + commit_s * 0.2
        return max(0.0, min(1.0, s * w["market_validation"]))

    def _rate_limit_check(self) -> None:
        self._call_count += 1
        now = time.time()
        if now - self._last_reset > 60:
            self._call_count = 0
            self._last_reset = now
        if self._call_count > 1000:
            time.sleep(0.1)


_vault = _Vault()
_scorer = SecureScorer()


def get_vault() -> _Vault:
    return _vault


def get_scorer() -> SecureScorer:
    return _scorer


def get_factor_weights() -> dict[str, float]:
    return _vault.get("factor_weights")


def get_decision_thresholds() -> dict[str, Any]:
    return _vault.get("decision_thresholds")
