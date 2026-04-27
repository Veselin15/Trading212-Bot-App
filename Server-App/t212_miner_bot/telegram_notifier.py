"""
Telegram notifier utility for the Trading 212 bot.

Design goals:
- Never crash the bot (missing env vars, network errors, Telegram downtime).
- Use short timeouts so notifications can't block trading execution.
- Keep a simple synchronous API; call it in a background task/thread from async code.
"""

from __future__ import annotations

import os
import requests


_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


def send_telegram_message(message: str) -> None:
    """
    Send a Telegram message using the Bot API.

    Environment variables:
      - TELEGRAM_BOT_TOKEN
      - TELEGRAM_CHAT_ID

    This function MUST NOT raise. It prints warnings and returns on any failure.
    """
    token = _TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = _CHAT_ID or os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("[WARN] Telegram notifier disabled: missing TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID")
        return

    text = str(message or "").strip()
    if not text:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    try:
        # Short timeouts so we never delay the trading loop.
        resp = requests.post(url, json=payload, timeout=(3.0, 6.0))
        if resp.status_code >= 400:
            print(f"[WARN] Telegram send failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as exc:
        print(f"[WARN] Telegram send failed: {exc}")

