"""SwiftTrade desktop — application entry (keeps ``MainWindow`` import stable for tests)."""
from __future__ import annotations

import asyncio
import sys

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from .main_window import MainWindow
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
