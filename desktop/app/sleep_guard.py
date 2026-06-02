"""Prevent Windows from sleeping while the bot is connected.

Uses SetThreadExecutionState so the OS keeps the CPU and network alive
even when the display turns off.  Completely safe on non-Windows — all
calls are no-ops on platforms where the API is unavailable.
"""
from __future__ import annotations

import sys

# Windows execution-state flags
_ES_CONTINUOUS           = 0x80000000
_ES_SYSTEM_REQUIRED      = 0x00000001
_ES_DISPLAY_REQUIRED     = 0x00000002
_ES_AWAYMODE_REQUIRED    = 0x00000040  # keep CPU running even on modern standby

# Combined flag: keep system + network alive, allow display to turn off
_AWAKE_FLAGS  = _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED | _ES_AWAYMODE_REQUIRED
_RESTORE_FLAG = _ES_CONTINUOUS   # restore all normal power-saving behaviour


def _stec():
    """Return the SetThreadExecutionState function, or None on non-Windows."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        fn = ctypes.windll.kernel32.SetThreadExecutionState  # type: ignore[attr-defined]
        fn.argtypes = [ctypes.c_uint32]
        fn.restype  = ctypes.c_uint32
        return fn
    except Exception:
        return None


class SleepGuard:
    """Acquire/release a Windows sleep-prevention hold.

    Usage::

        guard = SleepGuard()
        guard.acquire()   # PC won't sleep
        ...
        guard.release()   # normal sleep policy restored
    """

    def __init__(self) -> None:
        self._active = False
        self._fn = _stec()

    # ── public ────────────────────────────────────────────────────────────────

    def acquire(self) -> bool:
        """Prevent sleep.  Returns True if the OS accepted the request."""
        if self._active:
            return True
        if self._fn is None:
            return False
        try:
            prev = self._fn(_AWAKE_FLAGS)
            self._active = prev != 0
            return self._active
        except Exception:
            return False

    def release(self) -> None:
        """Restore normal OS sleep policy."""
        if not self._active:
            return
        try:
            if self._fn is not None:
                self._fn(_RESTORE_FLAG)
        except Exception:
            pass
        finally:
            self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def __del__(self) -> None:
        self.release()
