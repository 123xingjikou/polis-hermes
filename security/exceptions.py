"""Custom exception hierarchy for security errors."""


class SecurityError(Exception):
    """Base class for all security-related errors."""
    pass


class LicenseExpired(SecurityError):
    """Raised when license has expired."""
    pass


class LicenseInvalid(SecurityError):
    """Raised when license is invalid."""
    pass


class SignatureError(SecurityError):
    """Raised when code signature verification fails."""
    pass


class TamperDetected(SecurityError):
    """Raised when tampering is detected."""
    pass


class UnauthorizedMod(SecurityError):
    """Raised when unauthorized modification is detected."""
    pass


class DeviceMismatch(SecurityError):
    """Raised when device binding does not match."""
    pass
