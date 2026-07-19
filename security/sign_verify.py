"""Code Signing: RSA signature and SHA-256 integrity verification.

Provides RSA-based code signing with PyCryptodome.
Falls back to HMAC-SHA256 when PyCryptodome is not available.
"""

import hashlib
import hmac
import json
import os
import base64
from pathlib import Path
from typing import Any

from .exceptions import SignatureError, SecurityError


KEY_DIR = os.path.join(os.path.expanduser("~"), ".polis", "keys")
SIGNATURE_DIR = os.path.join(os.path.expanduser("~"), ".polis", "signatures")
ALGORITHM = "sha256"


class CodeSigner:
    """Sign and verify file integrity using RSA or HMAC."""

    def __init__(self, key_dir: str = KEY_DIR, sig_dir: str = SIGNATURE_DIR):
        self._key_dir = key_dir
        self._sig_dir = sig_dir
        os.makedirs(self._key_dir, exist_ok=True)
        os.makedirs(self._sig_dir, exist_ok=True)

    def __repr__(self) -> str:
        return "CodeSigner(protected)"

    def compute_hash(self, filepath: str) -> str:
        """Compute SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def generate_manifest(self, directory: str, glob: str = "*.py") -> dict[str, str]:
        """Generate file hash manifest for a directory."""
        manifest = {}
        dpath = Path(directory)
        for py_file in dpath.rglob(glob):
            rel = str(py_file.relative_to(dpath))
            manifest[rel] = self.compute_hash(str(py_file))
        return manifest

    def sign(self, manifest: dict[str, str]) -> bytes:
        """Create a signature for the manifest."""
        payload = json.dumps(manifest, sort_keys=True).encode()
        key = self._load_private_key()
        try:
            from Crypto.PublicKey import RSA
            from Crypto.Signature import pkcs1_15
            from Crypto.Hash import SHA256
            h = SHA256.new(payload)
            sig = pkcs1_15.new(key).sign(h)
            return base64.b64encode(sig)
        except Exception:
            sig = hmac.new(key, payload, hashlib.sha256).digest()
            return base64.b64encode(sig)

    def verify(self, manifest: dict[str, str], signature: bytes) -> bool:
        """Verify manifest against signature."""
        payload = json.dumps(manifest, sort_keys=True).encode()
        key = self._load_private_key()
        sig_bytes = base64.b64decode(signature)
        try:
            from Crypto.PublicKey import RSA
            from Crypto.Signature import pkcs1_15
            from Crypto.Hash import SHA256
            h = SHA256.new(payload)
            pkcs1_15.new(key).verify(h, sig_bytes)
            return True
        except Exception:
            expected = hmac.new(key, payload, hashlib.sha256).digest()
            return hmac.compare_digest(expected, sig_bytes)

    def verify_self(self, directory: str = "") -> bool:
        """Verify code integrity against stored manifest."""
        dpath = directory or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sig_file = os.path.join(self._sig_dir, "manifest.sig")
        manifest_file = os.path.join(self._sig_dir, "manifest.json")
        if not os.path.exists(sig_file) or not os.path.exists(manifest_file):
            return False
        with open(manifest_file) as f:
            stored_manifest = json.load(f)
        with open(sig_file, "rb") as f:
            signature = f.read()
        current_manifest = self.generate_manifest(dpath)
        if stored_manifest == current_manifest:
            return True
        return self.verify(current_manifest, signature)

    def verify_tree(self, directory: str) -> dict[str, Any]:
        """Verify full directory tree."""
        current = self.generate_manifest(directory)
        sig_file = os.path.join(self._sig_dir, "manifest.sig")
        manifest_file = os.path.join(self._sig_dir, "manifest.json")
        result = {"verified": False, "missing": [], "modified": [], "added": []}
        if not os.path.exists(manifest_file):
            return result
        with open(manifest_file) as f:
            stored = json.load(f)
        with open(sig_file, "rb") as f:
            sig = f.read()
        if not self.verify(current, sig):
            return result
        all_files = set(list(stored.keys()) + list(current.keys()))
        for f in all_files:
            if f not in stored:
                result["added"].append(f)
            elif f not in current:
                result["missing"].append(f)
            elif stored[f] != current[f]:
                result["modified"].append(f)
        result["verified"] = len(result["missing"]) == 0 and len(result["modified"]) == 0
        return result

    # ---------- key management ----------

    def _load_private_key(self) -> bytes:
        """Load or generate private key."""
        key_path = os.path.join(self._key_dir, "private.pem")
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()
        try:
            from Crypto.PublicKey import RSA
            key = RSA.generate(2048)
            with open(key_path, "wb") as f:
                f.write(key.export_key())
            pub_path = os.path.join(self._key_dir, "public.pem")
            with open(pub_path, "wb") as f:
                f.write(key.publickey().export_key())
            return key.export_key()
        except Exception:
            key = os.urandom(32)
            with open(key_path, "wb") as f:
                f.write(key)
            return key
