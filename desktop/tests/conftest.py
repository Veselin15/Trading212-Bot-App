from __future__ import annotations

import asyncio

import pytest
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop


@pytest.fixture
def qasync_loop(qtbot):
    """Use Qt's asyncio loop so MainWindow coroutines can touch widgets safely."""
    app = QApplication.instance()
    assert app is not None
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    yield loop
    if not loop.is_closed():
        loop.close()
