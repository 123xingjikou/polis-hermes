"""Device Binding: Hardware fingerprint generation and enforcement."""

import hashlib
import hmac
import json
import os
import platform
import subprocess
import sys
import uuid
from typing import Any

from .exceptions import DeviceMismatch, SecurityError

BINDING_DIR = os.path.join(os.path.expanduser("~"), ".polis", "bindings")
_BINDING_FILE = os.path.join(BINDING_DIR, "device.json")

_HW_WEIGHTS = {
    "cpu_id": 0.30,
    "mac_addr": 0.25,
    "disk_serial": 0.20,
    "board_serial": 0.15,
    "hostname": 0.10,
}


class DeviceBinder:
    """Generate hardware fingerprint and enforce device binding."""

    def __init__(self, binding_file: str = _BINDING_FILE):
        self._binding_file = binding_file
        os.makedirs(os.path.dirname(self._binding_file), exist_ok=True)

    def __repr__(self) -> str:
        return "DeviceBinder(protected)"

    def generate_fingerprint(self) -> str:
        """Generate composite hardware fingerprint."""
        components = self._collect_components()
        combined = "|".join(f"{k}={v}" for k, v in sorted(components.items()))
        hash_bytes = hashlib.sha256(combined.encode("utf-8")).digest()
        return hash_bytes.hex()[:32]

    def generate_weighted_token(self) -> dict[str, Any]:
        """Generate weighted fingerprint with component breakdown."""
        from datetime import datetime, timezone
        components = self._collect_components()
        component_hashes = {
            k: hashlib.sha256(v.encode()).hexdigest()[:16]
            for k, v in components.items()
        }
        weighted_sum = hashlib.sha256(
            json.dumps(component_hashes, sort_keys=True).encode()
        ).hexdigest()[:32]
        return {
            "fingerprint": weighted_sum,
            "components": component_hashes,
            "weights": _HW_WEIGHTS,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def bind(self, fingerprint: str = "") -> dict[str, Any]:
        """Bind current device, store binding info."""
        fp = fingerprint or self.generate_fingerprint()
        token = self.generate_weighted_token()
        binding = {
            "fingerprint": fp,
            "device_token": token,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }
        with open(self._binding_file, "w") as f:
            json.dump(binding, f, indent=2)
        return binding

    def enforce_binding(self, tolerance: float = 0.2) -> bool:
        """Verify current device matches stored binding."""
        if not os.path.exists(self._binding_file):
            self.bind()
            return True
        with open(self._binding_file) as f:
            stored: dict[str, Any] = json.load(f)
        stored_fp = stored.get("fingerprint", "")
        current_fp = self.generate_fingerprint()
        if hmac.compare_digest(stored_fp, current_fp):
            return True
        stored_components = stored.get("device_token", {}).get("components", {})
        current_components = self.generate_weighted_token().get("components", {})
        if not stored_components:
            return False
        mismatches = 0
        total = len(stored_components)
        for key, stored_hash in stored_components.items():
            current_hash = current_components.get(key, "")
            if not hmac.compare_digest(stored_hash, current_hash):
                mismatches += 1
        ratio = mismatches / total if total > 0 else 1.0
        if ratio <= tolerance:
            return True
        raise DeviceMismatch(
            f"Device binding failed: {mismatches}/{total} components mismatched"
        )

    def unbind(self) -> bool:
        """Remove binding file."""
        if os.path.exists(self._binding_file):
            os.remove(self._binding_file)
            return True
        return False

    def _collect_components(self) -> dict[str, str]:
        return {
            "cpu_id": self._get_cpu_id(),
            "mac_addr": self._get_primary_mac(),
            "disk_serial": self._get_disk_serial(),
            "board_serial": self._get_board_serial(),
            "hostname": platform.node(),
        }

    def _get_cpu_id(self) -> str:
        try:
            if sys.platform == "win32":
                return self._wmic_query("cpu", "ProcessorId") or ""
            if sys.platform == "linux":
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "serial" in line.lower() or "model name" in line.lower():
                            return line.split(":")[-1].strip()
            if sys.platform == "darwin":
                return self._sysctl("machdep.cpu.brand_string") or ""
        except Exception:
            pass
        return platform.processor() or "unknown_cpu"

    def _get_primary_mac(self) -> str:
        try:
            mac = uuid.getnode()
            if mac and mac != 0:
                return ":".join(f"{(mac >> ele) & 0xFF:02x}" for ele in range(40, -1, -8))
        except Exception:
            pass
        try:
            result = subprocess.run(
                ["getmac", "/v", "/fo", "csv"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            for line in lines[1:]:
                if "disconnected" not in line.lower():
                    parts = line.split(",")
                    if len(parts) >= 2:
                        return parts[1].strip().strip('"').lower()
        except Exception:
            pass
        return "00:00:00:00:00:00"

    def _get_disk_serial(self) -> str:
        try:
            if sys.platform == "win32":
                return self._wmic_query("diskdrive", "SerialNumber") or ""
            if sys.platform == "linux":
                result = subprocess.run(
                    ["lsblk", "-ndo", "SERIAL", "/dev/sda"],
                    capture_output=True, text=True, timeout=5
                )
                serial = result.stdout.strip()
                if serial:
                    return serial
            if sys.platform == "darwin":
                result = subprocess.run(
                    ["system_profiler", "SPStorageDataType"],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.split("\n"):
                    if "serial" in line.lower() and "number" in line.lower():
                        return line.split(":")[-1].strip()
        except Exception:
            pass
        return "UNKNOWN_DISK"

    def _get_board_serial(self) -> str:
        try:
            if sys.platform == "win32":
                return self._wmic_query("baseboard", "SerialNumber") or ""
            if sys.platform == "linux":
                paths = [
                    "/sys/class/dmi/id/board_serial",
                    "/sys/class/dmi/id/product_serial",
                ]
                for path in paths:
                    if os.path.exists(path):
                        with open(path, "r") as f:
                            serial = f.read().strip()
                            if serial and serial not in ("None", "To be filled by O.E.M."):
                                return serial
            if sys.platform == "darwin":
                result = subprocess.run(
                    ["system_profiler", "SPHardwareDataType"],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.split("\n"):
                    if "serial" in line.lower() and "system" in line.lower():
                        return line.split(":")[-1].strip()
        except Exception:
            pass
        return "UNKNOWN_BOARD"

    def _wmic_query(self, wmic_class: str, field: str) -> str:
        try:
            result = subprocess.run(
                ["wmic", wmic_class, "get", field],
                capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                value = lines[1].strip()
                if value and "value" not in value.lower():
                    return value
        except Exception:
            pass
        return ""

    def _sysctl(self, key: str) -> str:
        try:
            result = subprocess.run(
                ["sysctl", "-n", key],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception:
            pass
        return ""


class AttestationRequest:
    """Remote attestation for enterprise tier."""

    def __init__(self, device_binder: DeviceBinder, server_url: str = ""):
        self._binder = device_binder
        self._server = server_url or os.getenv(
            "POLIS_ATTESTATION_SERVER", "https://polis.example.com/attest"
        )

    def create_challenge(self) -> dict[str, Any]:
        from datetime import datetime, timezone
        return {
            "device_fp": self._binder.generate_fingerprint(),
            "token": self._binder.generate_weighted_token(),
            "nonce": os.urandom(16).hex(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
        }

    def attest(self, license_key: str) -> bool:
        challenge = self.create_challenge()
        challenge["license"] = license_key
        try:
            import urllib.request
            import ssl
            data = json.dumps(challenge).encode()
            req = urllib.request.Request(
                self._server,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                result = json.loads(resp.read())
                return result.get("approved", False)
        except Exception:
            return False
