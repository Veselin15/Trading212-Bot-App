"""SwiftTrade desktop — application entry (keeps ``MainWindow`` import stable for tests)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from .main_window import MainWindow
from .settings_store import SettingsStore
from .ui.first_run_dialog import run_first_run_dialog
from .ui.theme import apply_desktop_styles

__all__ = ["MainWindow", "main"]


def _center_on_primary_screen(window: MainWindow) -> None:
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return
    geo = screen.availableGeometry()
    frame = window.frameGeometry()
    frame.moveCenter(geo.center())
    window.move(frame.topLeft())


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("SwiftTrade")
    app.setOrganizationName("SwiftTrade")
    apply_desktop_styles(app)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Show terms/risk acceptance dialog on first launch.
    _base_dir = Path.home() / ".t212_executor"
    _store = SettingsStore(_base_dir)
    _settings = _store.load()
    if not _settings.terms_accepted:
        if not run_first_run_dialog():
            sys.exit(0)
        _settings.terms_accepted = True
        _store.save(_settings)

    w = MainWindow()
    _center_on_primary_screen(w)
    if getattr(w, "start_minimized", False):
        w.showMinimized()
    else:
        w.showNormal()
        w.raise_()
        w.activateWindow()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
