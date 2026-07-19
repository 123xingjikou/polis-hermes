"""Software protection: multi-layer defense against unauthorized modification.

Modules:
- sign_verify:  RSA code signing and SHA-256 integrity verification
- anti_tamper: anti-debug, bytecode hashing, watchdog thread
- license_mgr: AES-encrypted license files with hardware binding
- device_bind: hardware fingerprint generation and enforcement

Usage:
    from security import bootstrap
    bootstrap({"tier": "enterprise", "license_key": "XXXXX-XXXXX-..."})
"""

__version__ = "1.0.0"

from .sign_verify import CodeSigner
from .anti_tamper import Protector, guard
from .license_mgr import LicenseManager
from .device_bind import DeviceBinder, AttestationRequest
from .exceptions import SecurityError, LicenseExpired, SignatureError, TamperDetected, UnauthorizedMod, DeviceMismatch, LicenseInvalid


def bootstrap(config: dict | None = None) -> None:
    """Initialize security protections at application startup.

    Args:
        config: {
            "tier": "community" | "pro" | "enterprise",
            "license_key": "XXXXX-...",
            "server_url": "https://...",
        }
    """
    cfg_ = config or {}
    tier = cfg_.get("tier", "community")
    license_key = cfg_.get("license_key", "")

    # Layer 1: Code signing
    signer = CodeSigner()
    if not signer.verify_self():
        raise TamperDetected("Code signature verification failed!")

    # Layer 2: Anti-tamper
    if tier in ("pro", "enterprise"):
        Protector().enable_full_protection()

    # Layer 3: License validation
    if license_key:
        lm = LicenseManager()
        if not lm.validate(license_key):
            raise LicenseExpired("Invalid or expired license!")

    # Layer 4: Device binding
    if tier == "enterprise" and license_key:
        DeviceBinder().enforce_binding()


def require_feature(feature_name: str):
    """Decorator to gate a feature behind a license check."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper.__wrapped__ = func
        wrapper._feature = feature_name
        return wrapper
    return decorator


def publish_guard(func):
    """Decorator: verify integrity before publishing."""
    def wrapper(*args, **kwargs):
        Protector().verify_function_integrity(func)
        return func(*args, **kwargs)
    wrapper.__wrapped__ = func
    return wrapper
