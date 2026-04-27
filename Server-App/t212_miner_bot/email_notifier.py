from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from .config import GMAIL_PASSWORD, GMAIL_RECIPIENT, GMAIL_SENDER


logger = logging.getLogger(__name__)
_email_auth_warned = False


async def send_email_alert(subject: str, body: str) -> None:
    """Send an email alert without blocking the event loop."""
    if not GMAIL_SENDER or not GMAIL_PASSWORD:
        logger.error("Email alert skipped: GMAIL_SENDER or GMAIL_PASSWORD is missing.")
        return

    # Gmail App Passwords are often copied as grouped chunks with spaces.
    smtp_password = GMAIL_PASSWORD.replace(" ", "").strip()

    def _send_sync() -> None:
        message = EmailMessage()
        message["From"] = GMAIL_SENDER
        message["To"] = GMAIL_RECIPIENT
        message["Subject"] = subject.strip()
        message.set_content(body.strip())

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
            smtp.login(GMAIL_SENDER, smtp_password)
            smtp.send_message(message)

    try:
        await asyncio.to_thread(_send_sync)
    except smtplib.SMTPAuthenticationError as exc:
        global _email_auth_warned
        if not _email_auth_warned:
            smtp_code = getattr(exc, "smtp_code", "unknown")
            smtp_error = getattr(exc, "smtp_error", b"")
            decoded_error = (
                smtp_error.decode("utf-8", errors="ignore")
                if isinstance(smtp_error, (bytes, bytearray))
                else str(smtp_error)
            )
            logger.warning(
                "[WARN] Email auth failed (code=%s): %s",
                smtp_code,
                decoded_error or "no smtp error details",
            )
            _email_auth_warned = True
    except Exception as exc:
        # Keep the trading bot alive even when email delivery fails.
        logger.error("Failed to send email alert: %s", exc)
