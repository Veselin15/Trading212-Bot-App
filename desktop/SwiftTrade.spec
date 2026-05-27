# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for SwiftTrade Desktop Executor.
# Run from the desktop/ directory:  pyinstaller SwiftTrade.spec --clean --noconfirm
# Or use:  desktop\scripts\build-windows.ps1

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

_spec_dir = Path(os.path.abspath(SPEC)).parent
_app_hidden = collect_submodules("app")
_datas = [
    # Bundle the repo logo so the navbar icon works in the frozen exe.
    # paths.py returns sys._MEIPASS when frozen, so logo.png must be at its root.
    (str(_spec_dir.parent / "logo.png"), "."),
    # Version constant — also imported as a normal module, but this makes the file
    # visible at the MEIPASS root for any direct-path reads if needed.
    (str(_spec_dir / "app" / "__version__.py"), "app"),
]
_ed = _spec_dir / "executor_defaults.json"
if _ed.is_file():
    # Written by build-windows.ps1 -DefaultExecutorWsUrl (release → your cloud signal server)
    _datas.append((str(_ed), "."))

a = Analysis(
    # entry.py imports app.main as a package — avoids "relative import" errors in the EXE.
    ["entry.py"],
    pathex=[str(_spec_dir)],
    binaries=[],
    datas=_datas,
    hiddenimports=_app_hidden + [
        # Qt / PySide6 — PyInstaller's built-in hooks cover the core modules,
        # but explicit entries avoid "No module named …" errors at runtime.
        "PySide6.QtWidgets",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtNetwork",
        # qasync integrates asyncio with the Qt event loop; it's not auto-detected.
        "qasync",
        # websockets 16 — the asyncio-native API plus the legacy shim.
        "websockets",
        "websockets.asyncio",
        "websockets.asyncio.client",
        "websockets.asyncio.connection",
        "websockets.asyncio.server",
        "websockets.exceptions",
        "websockets.frames",
        "websockets.http11",
        "websockets.legacy",
        "websockets.legacy.client",
        "websockets.legacy.server",
        # cryptography — Fernet + PBKDF2 key derivation used by crypto_store.py
        "cryptography",
        "cryptography.fernet",
        "cryptography.hazmat.primitives",
        "cryptography.hazmat.primitives.kdf",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
        "cryptography.hazmat.backends",
        "cryptography.hazmat.backends.openssl",
        "cryptography.hazmat.backends.openssl.backend",
        # aiohttp — used by t212_client.py for Trading212 REST calls
        "aiohttp",
        "aiohttp.connector",
        "aiohttp.client",
        "aiohttp.client_reqrep",
        "aiohttp.http_parser",
        "aiohttp.http_websocket",
        "aiohttp.streams",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude heavy packages that are definitely not needed in the desktop app.
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "PIL",
        "pytest",
        "numpy",
        "pandas",
        "yfinance",
        "sqlalchemy",
        "alembic",
        "fastapi",
        "uvicorn",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# One-file executable: all binaries and data are packed inside the .exe.
# On first run Windows extracts to %TEMP%\MEIxxxxxx; subsequent launches reuse the cache.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SwiftTrade",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # No console window — this is a GUI app.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Optionally add a Windows .ico file:  icon="assets/SwiftTrade.ico"
)
