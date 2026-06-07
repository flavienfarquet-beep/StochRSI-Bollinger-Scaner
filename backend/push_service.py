"""Web Push (VAPID) notification service."""
from __future__ import annotations

import json
import logging
import os
from typing import Tuple

from pywebpush import WebPushException, webpush

logger = logging.getLogger(__name__)


def _vapid_claims() -> dict:
    contact = os.environ.get("VAPID_CONTACT", "mailto:admin@example.com").strip()
    return {"sub": contact}


def send_push(subscription_info: dict, title: str, body: str, data: dict | None = None) -> Tuple[bool, str]:
    """Send a push notification to a single subscription. Returns (success, message)."""
    private_key = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    if not private_key:
        return False, "VAPID_PRIVATE_KEY not configured."
    payload = json.dumps({
        "title": title,
        "body": body,
        "data": data or {},
    })
    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=private_key,
            vapid_claims=_vapid_claims(),
        )
        return True, "Push delivered"
    except WebPushException as e:
        # 404 / 410 = subscription expired or unsubscribed
        status = getattr(e, "response", None)
        code = status.status_code if status is not None else None
        msg = f"WebPush error (status={code}): {e}"
        logger.warning(msg)
        return False, msg
    except Exception as e:
        msg = f"WebPush unexpected error: {e}"
        logger.exception(msg)
        return False, msg


def is_gone(message: str) -> bool:
    """Detect expired/unsubscribed (HTTP 404/410) from error message."""
    return "status=404" in message or "status=410" in message
