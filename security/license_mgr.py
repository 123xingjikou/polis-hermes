"""License Manager: AES-encrypted license files with hardware binding."""

import hashlib
import hmac
import json
import os
import struct
import time
import zlib
from datetime import datetime, timedelta
from typing import Any

from .exceptions import LicenseExpired, LicenseInvalid, SecurityError

LICENSE_DIR = os.path.join(os.path.expanduser("~"), ".polis", "licenses")
_LICENSE_MAGIC = b"PLIC"
_LICENSE_VERSION = 1


class LicenseManager:
    """Create, encrypt, store, and verify license files."""

    def __init__(self, key: str = "", license_dir: str = LICENSE_DIR):
        self._key = key or os.getenv("POLIS_LICENSE_KEY", "polis-default-dev-key-2024")
        self._dir = license_dir
        os.makedirs(self._dir, exist_ok=True)

    def __repr__(self) -> str:
        return "LicenseManager(protected)"

    def issue(
        self,
        customer: str,
        tier: str,
        days_valid: int = 365,
        hw_fingerprint: str = "",
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Issue a new license and return the license key string."""
        payload = {
            "customer": customer,
            "tier": tier,
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=days_valid)).isoformat(),
            "hw_fingerprint": hw_fingerprint,
            "features": extra or {},
        }
        raw = self._serialize(payload)
        encrypted = self._encrypt(raw)
        lic_key = self._encode_key(encrypted)
        self._save_to_disk(lic_key, encrypted)
        return lic_key

    def validate(self, lic_key: str) -> bool:
        """Validate license key. Returns True if valid."""
        try:
            encrypted = self._decode_key(lic_key)
            raw = self._decrypt(encrypted)
            payload = self._deserialize(raw)
        except Exception:
            return False
        if not self._check_expiry(payload):
            raise LicenseExpired(f"License expired at {payload.get('expires_at')}")
        if not self._check_hardware(payload):
            raise LicenseInvalid("License not valid for this device")
        return True

    def revoke(self, lic_key: str) -> bool:
        """Revoke (delete) a license file."""
        try:
            encrypted = self._decode_key(lic_key)
            fname = self._key_to_filename(lic_key)
            path = os.path.join(self._dir, fname)
            if os.path.exists(path):
                os.remove(path)
                return True
            return False
        except Exception:
            return False

    def info(self, lic_key: str) -> dict[str, Any]:
        """Return license metadata without validation."""
        encrypted = self._decode_key(lic_key)
        raw = self._decrypt(encrypted)
        return self._deserialize(raw)

    def list_licenses(self) -> list[str]:
        """List all stored license keys."""
        if not os.path.isdir(self._dir):
            return []
        result = []
        for fname in os.listdir(self._dir):
            if fname.endswith(".lic"):
                path = os.path.join(self._dir, fname)
                try:
                    with open(path, "rb") as f:
                        encrypted = f.read()
                    raw = self._decrypt(encrypted)
                    payload = self._deserialize(raw)
                    result.append({
                        "customer": payload.get("customer", ""),
                        "tier": payload.get("tier", ""),
                        "expires_at": payload.get("expires_at", ""),
                    })
                except Exception:
                    continue
        return result

    def _serialize(self, payload: dict[str, Any]) -> bytes:
        payload_bytes = json.dumps(payload).encode("utf-8")
        issued_ts = int(datetime.fromisoformat(payload["issued_at"]).timestamp())
        expires_ts = int(datetime.fromisoformat(payload["expires_at"]).timestamp())
        hw_fp = payload.get("hw_fingerprint", "")[:32].ljust(32).encode("ascii")
        header = struct.pack(
            "<4sBBQQ32s",
            _LICENSE_MAGIC, _LICENSE_VERSION, 0,
            issued_ts, expires_ts, hw_fp,
        )
        return header + payload_bytes

    def _deserialize(self, raw: bytes) -> dict[str, Any]:
        if len(raw) < 54:
            raise LicenseInvalid("License too short")
        header = raw[:54]
        payload_bytes = raw[54:]
        magic, version, flags, issued_ts, expires_ts, hw_fp = struct.unpack(
            "<4sBBQQ32s", header
        )
        if magic != _LICENSE_MAGIC:
            raise LicenseInvalid("Invalid license magic")
        if version != _LICENSE_VERSION:
            raise LicenseInvalid(f"Unsupported license version: {version}")
        payload = json.loads(payload_bytes.decode("utf-8"))
        payload["_issued_ts"] = issued_ts
        payload["_expires_ts"] = expires_ts
        payload["_hw_fp"] = hw_fp.decode("ascii").strip()
        return payload

    def _derive_key(self, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", self._key.encode(), salt, 100_000, dklen=32)

    def _encrypt(self, plaintext: bytes) -> bytes:
        salt = os.urandom(16)
        nonce = os.urandom(12)
        derived = self._derive_key(salt)
        try:
            from Crypto.Cipher import AES
            cipher = AES.new(derived, AES.MODE_GCM, nonce=nonce)
            ciphertext, tag = cipher.encrypt_and_digest(plaintext)
            return salt + nonce + tag + ciphertext
        except Exception:
            keystream = self._xor_keystream(derived, len(plaintext))
            enc = bytes(a ^ b for a, b in zip(plaintext, keystream))
            mac = hmac.new(derived, salt + nonce + enc, hashlib.sha256).digest()
            return salt + nonce + mac + enc

    def _decrypt(self, encrypted: bytes) -> bytes:
        if len(encrypted) < 56:
            raise LicenseInvalid("License data too short")
        salt = encrypted[:16]
        nonce = encrypted[16:28]
        derived = self._derive_key(salt)
        try:
            from Crypto.Cipher import AES
            tag = encrypted[28:44]
            ciphertext = encrypted[44:]
            cipher = AES.new(derived, AES.MODE_GCM, nonce=nonce)
            return cipher.decrypt_and_verify(ciphertext, tag)
        except Exception:
            mac = encrypted[28:60]
            ciphertext = encrypted[60:]
            expected_mac = hmac.new(derived, salt + nonce + ciphertext, hashlib.sha256).digest()
            if not hmac.compare_digest(mac, expected_mac):
                raise LicenseInvalid("License integrity check failed")
            keystream = self._xor_keystream(derived, len(ciphertext))
            return bytes(a ^ b for a, b in zip(ciphertext, keystream))

    def _xor_keystream(self, key: bytes, length: int) -> bytes:
        keystream = b""
        counter = 0
        while len(keystream) < length:
            block = hashlib.sha256(key + struct.pack("<Q", counter)).digest()
            keystream += block
            counter += 1
        return keystream[:length]

    def _encode_key(self, encrypted: bytes) -> str:
        compressed = zlib.compress(encrypted, 9)
        encoded = self._base32_encode(compressed)
        groups = [encoded[i:i+5] for i in range(0, len(encoded), 5)]
        return "-".join(groups)

    def _decode_key(self, lic_key: str) -> bytes:
        stripped = lic_key.replace("-", "").replace(" ", "").upper()
        compressed = self._base32_decode(stripped)
        return zlib.decompress(compressed)

    @staticmethod
    def _base32_encode(data: bytes) -> str:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
        result = []
        bits = 0
        value = 0
        for byte in data:
            value = (value << 8) | byte
            bits += 8
            while bits >= 5:
                result.append(alphabet[(value >> (bits - 5)) & 31])
                bits -= 5
        if bits > 0:
            result.append(alphabet[(value << (5 - bits)) & 31])
        return "".join(result)

    @staticmethod
    def _base32_decode(encoded: str) -> bytes:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
        decode_map = {c: i for i, c in enumerate(alphabet)}
        bits = 0
        value = 0
        result = bytearray()
        for char in encoded:
            if char not in decode_map:
                continue
            value = (value << 5) | decode_map[char]
            bits += 5
            if bits >= 8:
                result.append((value >> (bits - 8)) & 0xFF)
                bits -= 8
        return bytes(result)

    def _check_expiry(self, payload: dict[str, Any]) -> bool:
        expires_ts = payload.get("_expires_ts", 0)
        return time.time() < expires_ts

    def _check_hardware(self, payload: dict[str, Any]) -> bool:
        bound_fp = payload.get("_hw_fp", "")
        if not bound_fp:
            return True
        try:
            from .device_bind import DeviceBinder
            current_fp = DeviceBinder().generate_fingerprint()
            return hmac.compare_digest(bound_fp, current_fp[:32])
        except Exception:
            return True

    def _key_to_filename(self, lic_key: str) -> str:
        digest = hashlib.sha256(lic_key.encode()).hexdigest()[:16]
        return f"{digest}.lic"

    def _save_to_disk(self, lic_key: str, encrypted: bytes) -> None:
        fname = self._key_to_filename(lic_key)
        path = os.path.join(self._dir, fname)
        with open(path, "wb") as f:
            f.write(encrypted)
