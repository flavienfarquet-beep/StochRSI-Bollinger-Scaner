"""Resend email notification service."""
from __future__ import annotations

import logging
import os
from typing import Tuple

import resend

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_content: str) -> Tuple[bool, str]:
    """Send a transactional email via Resend. Returns (success, message)."""
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev").strip()

    if not api_key:
        return False, "RESEND_API_KEY is not configured in backend/.env."
    if not to:
        return False, "No recipient email configured. Set one in Settings → Notification Email."

    resend.api_key = api_key
    params = {
        "from": sender,
        "to": [to],
        "subject": subject,
        "html": html_content,
    }
    try:
        result = resend.Emails.send(params)
        email_id = result.get("id") if isinstance(result, dict) else None
        return True, f"Email sent (id={email_id})"
    except Exception as e:
        msg = f"Resend error: {e}"
        logger.exception(msg)
        return False, msg


def build_alert_email(alert_type: str, symbol: str, details: dict) -> Tuple[str, str]:
    """Return (subject, html_content) for an alert."""
    titles = {
        "oversold": f"[RSI Tracker] {symbol} — RSI Oversold",
        "overbought": f"[RSI Tracker] {symbol} — RSI Overbought",
        "golden_cross": f"[RSI Tracker] {symbol} — Golden Cross",
        "death_cross": f"[RSI Tracker] {symbol} — Death Cross",
        "combo_bullish": f"[RSI Tracker] {symbol} — Combo Bullish (RSI + Golden Cross)",
        "combo_bearish": f"[RSI Tracker] {symbol} — Combo Bearish (RSI + Death Cross)",
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
