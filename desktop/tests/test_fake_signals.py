"""
Inject fake WebSocket-style signal payloads into MainWindow._handle_signal
and assert UI / branching behaves as expected (no real broker or network).
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from websockets.exceptions import ConnectionClosed

from app.main import MainWindow
from app.t212_client import T212_API_DEMO_BASE, T212_API_LIVE_BASE, T212APIError
from app.ws_client import ExecWsClient, WsConfig


def _fake_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "fake-sig-001",
        "type": "ENTRY",
        "direction": "LONG",
        "symbol": "FAKE",
        "risk_params": {"stop_loss_pct": 2.0, "take_profit_pct": 6.0},
    }
    base.update(overrides)
    return base


@pytest.fixture
def window(qtbot, tmp_path: Path, qasync_loop):
    w = MainWindow(base_dir=tmp_path)
    qtbot.addWidget(w)
    return w


def test_paper_mode_logs_signal_to_queue_and_table(window, qasync_loop):
    assert window.trading_mode.is_live() is False

    async def run():
        await window._handle_signal(_fake_payload(id="p1", symbol="ZZZ"))

    qasync_loop.run_until_complete(run())

    assert window._signal_count == 1
    assert window.signals_table.rowCount() == 1
    # Initial placeholder row remains until user clears it; newest signal is at index 0.
    assert window.exec_queue.item(0).text().find("p1") >= 0
    log = window.event_log.toPlainText()
    assert "Signal received" in log
    assert "Paper trading" in log
    assert "ZZZ" in log


def test_paper_mode_multiple_signals_newest_first(window, qasync_loop):
    async def run():
        await window._handle_signal(_fake_payload(id="a", symbol="AAA"))
        await window._handle_signal(_fake_payload(id="b", symbol="BBB"))

    qasync_loop.run_until_complete(run())

    assert window._signal_count == 2
    assert window.signals_table.item(0, 1).text() == "b"


def test_activity_filter_hides_non_matching_rows(window, qasync_loop):
    async def run():
        await window._handle_signal(_fake_payload(id="x", symbol="KEEP"))
        await window._handle_signal(_fake_payload(id="y", symbol="HIDE"))

    qasync_loop.run_until_complete(run())
    assert window.signals_table.rowCount() == 2

    window.activity_symbol_filter.setText("KEEP")
    window._on_filter_changed("")
    assert window.signals_table.rowCount() == 1
    assert window.signals_table.item(0, 3).text() == "KEEP"


def test_live_short_skipped_before_broker(window, qasync_loop):
    window.trading_mode.set_pro_unlocked(True)
    window.trading_mode.set_live(True)
    window._license_tier = "pro"
    window._confirm_before_trade = False
    window._skip_non_long_signals = True

    async def run():
        await window._handle_signal(_fake_payload(id="s1", direction="SHORT", symbol="SHORTSYM"))

    qasync_loop.run_until_complete(run())

    log = window.event_log.toPlainText()
    assert "Skipped (direction=SHORT)" in log
    assert "T212 keys missing" not in log


def test_live_long_no_keys_reports_error(window, qasync_loop):
    window.trading_mode.set_pro_unlocked(True)
    window.trading_mode.set_live(True)
    window._license_tier = "pro"
    window._confirm_before_trade = False
    window._skip_non_long_signals = True

    async def run():
        await window._handle_signal(_fake_payload(id="l1", direction="LONG", symbol="NOK"))

    qasync_loop.run_until_complete(run())

    assert "T212 keys missing" in window.event_log.toPlainText()  # substring of full message


def test_live_non_pro_blocks_and_forces_paper(window, qasync_loop):
    window.trading_mode.set_pro_unlocked(True)
    window.trading_mode.set_live(True)
    window._license_tier = "free"
    window._confirm_before_trade = False

    async def run():
        await window._handle_signal(_fake_payload())

    qasync_loop.run_until_complete(run())

    assert window.trading_mode.is_live() is False
    assert "not Pro" in window.event_log.toPlainText()


def test_t212_base_url_demo_when_not_pro(window, qasync_loop):
    window._license_tier = "free"
    assert window._t212_base_url() == T212_API_DEMO_BASE


def test_t212_base_url_live_when_pro_and_live_trading(window, qasync_loop):
    window._license_tier = "pro"
    window.trading_mode.set_pro_unlocked(True)
    window.trading_mode.set_live(True)
    assert window._t212_base_url() == T212_API_LIVE_BASE


def test_t212_base_url_demo_when_pro_but_paper(window, qasync_loop):
    window._license_tier = "pro"
    window.trading_mode.set_pro_unlocked(True)
    window.trading_mode.set_live(False)
    assert window._t212_base_url() == T212_API_DEMO_BASE


def test_live_test_button_disabled_for_non_pro(window, qasync_loop):
    window._license_tier = "free"
    window._update_broker_keys_hint()
    assert window.test_t212_practice_btn.isEnabled()
    assert not window.test_t212_live_btn.isEnabled()


def test_live_key_detection_non_pro_blocked(window, qasync_loop):
    """Non-Pro + 401 on demo but live probe succeeds → blocked with descriptive error."""
    window._license_tier = "free"
    window.practice_t212_api_key.setText("LIVE_KEY_FAKE")

    demo_error = T212APIError("GET /api/v0/equity/account/cash failed (401): ")
    call_log: list[str] = []

    class FakeClientDemo:
        def __init__(self, *_a, **_kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_): return False
        async def get_free_funds(self): raise demo_error
        async def get_pending_orders(self): return []  # not called by test but satisfies interface

    class FakeClientLive:
        def __init__(self, *_a, **_kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_): return False
        async def get_free_funds(self):
            call_log.append("live_probe")
            return 9999.0
        async def get_pending_orders(self): return []

    def patched_t212_client(*, keys, base_url="", **kw):
        return FakeClientLive() if base_url != T212_API_DEMO_BASE else FakeClientDemo()

    async def run():
        with patch("app.main_window.T212Client", side_effect=patched_t212_client):
            with patch("app.main_window.QMessageBox.critical"):
                # Call the underlying coroutine directly (bypass asyncSlot decorator)
                await MainWindow.on_test_t212_practice_clicked.__wrapped__(window)

    qasync_loop.run_until_complete(run())

    log = window.event_log.toPlainText()
    assert "real-money (Invest) key detected" in log
    assert "live_probe" in call_log


def test_live_key_detection_non_pro_generic_401(window, qasync_loop):
    """Non-Pro + 401 on both demo AND live → generic error, no live-key-detected message."""
    window._license_tier = "free"
    window.practice_t212_api_key.setText("BAD_KEY")

    demo_error = T212APIError("GET /api/v0/equity/account/cash failed (401): ")

    class FakeBothFail:
        def __init__(self, *_a, **_kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_): return False
        async def get_free_funds(self): raise demo_error
        async def get_pending_orders(self): return []

    async def run():
        with patch("app.main_window.T212Client", side_effect=lambda **kw: FakeBothFail()):
            with patch("app.main_window.QMessageBox.critical"):
                await MainWindow.on_test_t212_practice_clicked.__wrapped__(window)

    qasync_loop.run_until_complete(run())

    log = window.event_log.toPlainText()
    assert "T212 test failed" in log
    assert "real-money (Invest) key detected" not in log


def test_exec_ws_client_dispatches_signal_payload(qasync_loop):
    """Fake server: WELCOME, PING, SIGNAL, then close — ``on_signal`` must run once."""
    seen: list[dict[str, Any]] = []

    async def on_signal(payload: dict[str, Any]) -> None:
        seen.append(dict(payload))

    client = ExecWsClient(
        cfg=WsConfig(
            url="ws://unused",
            license_key="test-license",
            reconnect_interval_s=1,
            max_reconnect_attempts=1,
        ),
        on_status=lambda s: None,
        on_event=lambda e: None,
        on_signal=on_signal,
        on_bot_snapshot=lambda p: None,
    )

    class FakeWs:
        def __init__(self) -> None:
            self._n = 0

        async def send(self, _data: str) -> None:
            return None

        async def recv(self) -> str:
            self._n += 1
            if self._n == 1:
                return json.dumps({"type": "WELCOME"})
            if self._n == 2:
                return json.dumps({"type": "PING"})
            if self._n == 3:
                return json.dumps(
                    {
                        "type": "SIGNAL",
                        "payload": {"id": "ws-1", "direction": "LONG", "symbol": "MOCK"},
                    }
                )
            raise ConnectionClosed(1000, "bye")

    @asynccontextmanager
    async def fake_connect(*_a: Any, **_kw: Any):
        yield FakeWs()

    async def go() -> None:
        with patch("app.ws_client.websockets.connect", fake_connect):
            await client.run_forever()

    qasync_loop.run_until_complete(go())
    assert len(seen) == 1
    assert seen[0]["id"] == "ws-1"
    assert seen[0]["symbol"] == "MOCK"

