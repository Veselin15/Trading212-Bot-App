"""Register / deregister the app in the Windows startup registry key.

HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run
  SwiftTrade  ->  "C:\\path\\to\\SwiftTrade.exe" --minimized

Works only inside the frozen EXE on Windows.  All methods are safe no-ops
in development (non-frozen) or on non-Windows platforms.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REG_KEY  = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "SwiftTrade"


def _is_available() -> bool:
    """True only when running as a frozen Windows EXE."""
    return sys.platform == "win32" and getattr(sys, "frozen", False)


def _exe_path() -> str:
    """Absolute path to the running EXE."""
    return str(Path(sys.executable).resolve())


def enable() -> bool:
    """Add SwiftTrade to Windows startup.  Returns True on success."""
    if not _is_available():
        return False
    try:
        import winreg
        exe = _exe_path()
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, f'"{exe}" --minimized')
        return True
    except Exception:
        return False


def disable() -> bool:
    """Remove SwiftTrade from Windows startup.  Returns True on success."""
    if not _is_available():
        return False
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            try:
                winreg.DeleteValue(key, _APP_NAME)
            except FileNotFoundError:
                pass  # already absent — that's fine
        return True
    except Exception:
        return False


def is_enabled() -> bool:
    """Return True if the startup registry value currently exists."""
    if not _is_available():
        return False
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_READ
        ) as key:
            winreg.QueryValueEx(key, _APP_NAME)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
