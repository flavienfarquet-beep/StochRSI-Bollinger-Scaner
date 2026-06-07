"""SendGrid email notification service."""
from __future__ import annotations

import logging
import os
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_content: str) -> tuple[bool, str]:
    """Send a transactional email via SendGrid. Returns (success, message)."""
    api_key = os.environ.get("SENDGRID_API_KEY", "").strip()
    sender = os.environ.get("SENDER_EMAIL", "").strip()

    if not api_key:
        return False, "SENDGRID_API_KEY is not configured in backend/.env."
    if not sender:
        return False, "SENDER_EMAIL is not configured in backend/.env (must be a SendGrid-verified sender)."
    if not to:
        return False, "No recipient email configured. Set one in Settings → Notification Email."

    message = Mail(
        from_email=sender,
        to_emails=to,
        subject=subject,
        html_content=html_content,
    )
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        if 200 <= response.status_code < 300:
            return True, "Email sent."
        body = response.body.decode() if isinstance(response.body, bytes) else str(response.body)
        return False, f"SendGrid returned status {response.status_code}: {body}"
    except Exception as e:
        # SendGrid often raises HTTPError with .body
        body = getattr(e, "body", None)
        if isinstance(body, bytes):
            body = body.decode(errors="ignore")
        msg = f"SendGrid error: {e}" + (f" — {body}" if body else "")
        logger.exception(msg)
        return False, msg


def build_alert_email(alert_type: str, symbol: str, details: dict) -> tuple[str, str]:
    """Return (subject, html_content) for an alert."""
    titles = {
        "oversold": f"[RSI Tracker] {symbol} — RSI Oversold",
        "overbought": f"[RSI Tracker] {symbol} — RSI Overbought",
        "golden_cross": f"[RSI Tracker] {symbol} — Golden Cross",
        "death_cross": f"[RSI Tracker] {symbol} — Death Cross",
        "combo_bullish": f"[RSI Tracker] {symbol} — ⚡ Combo Bullish (RSI + Golden Cross)",
        "combo_bearish": f"[RSI Tracker] {symbol} — ⚡ Combo Bearish (RSI + Death Cross)",
    }
    subject = titles.get(alert_type, f"[RSI Tracker] {symbol} — {alert_type}")
    rows = "".join(
        f"<tr><td style='padding:6px 12px;color:#6B7280;font-family:monospace;font-size:12px;text-transform:uppercase;'>{k}</td>"
        f"<td style='padding:6px 12px;font-family:monospace;font-size:13px;color:#111827;'>{v}</td></tr>"
        for k, v in details.items()
    )
    html = f"""
    <div style="font-family:'IBM Plex Sans',Arial,sans-serif;max-width:560px;margin:0 auto;background:#F8F9FA;padding:24px;">
      <div style="background:#FFFFFF;border:1px solid #E5E7EB;padding:24px;">
        <p style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#9CA3AF;margin:0 0 8px;">RSI &amp; MA Tracker — Signal</p>
        <h1 style="font-size:22px;margin:0 0 4px;color:#111827;font-weight:500;">{symbol}</h1>
        <p style="margin:0 0 16px;color:#6B7280;font-size:14px;">Alert: <strong>{alert_type.replace('_',' ').title()}</strong></p>
        <table style="width:100%;border-collapse:collapse;border-top:1px solid #E5E7EB;">{rows}</table>
      </div>
    </div>
    """
    return subject, html
