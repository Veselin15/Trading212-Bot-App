"""SwiftTrade desktop — application entry (keeps ``MainWindow`` import stable for tests)."""
from __future__ import annotations

import asyncio
import sys

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from .main_window import MainWindow
from .ui.theme import apply_desktop_styles

__all__ = ["MainWindow", "main"]


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("SwiftTrade")
    app.setOrganizationName("SwiftTrade")
    apply_desktop_styles(app)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    w = MainWindow()
    if getattr(w, "start_minimized", False):
        w.showMinimized()
    else:
        w.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
