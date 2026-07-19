"""Anti-tampering: anti-debug, code integrity, self-modifying checks."""

import ctypes
import dis
import hashlib
import inspect
import os
import sys
import threading
import time
import types
from typing import Callable

from .exceptions import TamperDetected, UnauthorizedMod


class Protector:
    """Guards against debugging and code modification."""

    def __init__(self):
        self._active = False
        self._watchdog: threading.Thread | None = None
        self._stop_evt = threading.Event()
        self._original_hashes: dict[str, str] = {}

    def __repr__(self) -> str:
        return "Protector(active={})".format(self._active)

    # ---------- public API ----------

    def enable_full_protection(self) -> None:
        """Start all protections."""
        self._active = True
        self._snapshot_self()
        self._start_watchdog()
        self._check_debugger()

    def disable(self) -> None:
        self._active = False
        self._stop_evt.set()

    def verify_function_integrity(self, func: Callable) -> bool:
        """Re-hash bytecode of func and compare to snapshot."""
        key = f"{func.__module__}.{func.__qualname__}"
        current = self._hash_code(func)
        return self._original_hashes.get(key) == current

    # ---------- internals ----------

    def _hash_code(self, func: Callable) -> str:
        code = func.__code__
        raw = bytes()
        for const in code.co_consts:
            if isinstance(const, types.CodeType):
                raw += const.co_code
            else:
                raw += str(const).encode()
        raw += code.co_code
        return hashlib.sha256(raw).hexdigest()[:16]

    def _snapshot_self(self) -> None:
        """Hash every function in the security package."""
        import security as sec
        for name, obj in inspect.getmembers(sec, inspect.isfunction):
            key = f"sec.{name}"
            self._original_hashes[key] = self._hash_code(obj)
        for cls_name, cls in inspect.getmembers(sec, inspect.isclass):
            for name, method in inspect.getmembers(cls, inspect.isfunction):
                key = f"sec.{cls_name}.{name}"
                try:
                    self._original_hashes[key] = self._hash_code(method)
                except Exception:
                    pass

    def _check_debugger(self) -> None:
        """Detect common debuggers."""
        if sys.platform == "win32":
            kernel32 = ctypes.windll.kernel32
            if kernel32.IsDebuggerPresent():
                self._handle_violation("Debugger detected (IsDebuggerPresent)")
        if os.environ.get("PYTHONBREAKPOINT"):
            self._handle_violation("PYTHONBREAKPOINT is set")
        try:
            import pdb
            if pdb.Pdb._in_debugger:
                self._handle_violation("pdb in debugger state")
        except Exception:
            pass

    def _watchdog_loop(self) -> None:
        while not self._stop_evt.wait(timeout=2):
            try:
                self._check_debugger()
                self._verify_live()
            except Exception as e:
                self._handle_violation(f"Watchdog: {e}")

    def _start_watchdog(self) -> None:
        self._watchdog = threading.Thread(
            target=self._watchdog_loop, daemon=True, name="polis_protector"
        )
        self._watchdog.start()

    def _verify_live(self) -> None:
        import security as sec
        for name, orig_hash in self._original_hashes.items():
            parts = name.split(".")
            if len(parts) == 2:
                obj = getattr(sec, parts[1], None)
            elif len(parts) == 3:
                cls = getattr(sec, parts[1], None)
                obj = getattr(cls, parts[2], None) if cls else None
            else:
                continue
            if obj is None:
                continue
            cur = self._hash_code(obj)
            if cur != orig_hash:
                self._handle_violation(f"Code modified: {name}")

    def _handle_violation(self, reason: str) -> None:
        """React to detected tampering."""
        import logging
        logging.critical("TAMPER DETECTED: %s", reason)
        self._active = False
        self._stop_evt.set()
        threading.Thread(target=lambda: (time.sleep(0.5), os._exit(1)), daemon=True).start()
        raise TamperDetected(reason)


def guard(func: Callable) -> Callable:
    """Decorator: wrap function with runtime integrity check."""
    protector = Protector()
    protector._snapshot_self()

    def wrapper(*args, **kwargs):
        if not protector.verify_function_integrity(func):
            raise UnauthorizedMod(f"Function {func.__qualname__} was tampered with")
        return func(*args, **kwargs)
    wrapper.__wrapped__ = func
    return wrapper
