"""Yahoo Finance data fetching."""
from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

import yfinance as yf
from curl_cffi import requests as cffi_requests

logger = logging.getLogger(__name__)

# Persistent session impersonating Chrome to avoid Yahoo's bot blocks.
_session = cffi_requests.Session(impersonate="chrome")


def fetch_history(symbol: str, period: str = "1y", max_retries: int = 3) -> Optional[Dict]:
    """Fetch daily OHLC history for a ticker.

    Returns dict with keys: symbol, name, closes (list[float]), dates (list[str ISO]),
    currency, last_price. Returns None if not found.
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            ticker = yf.Ticker(symbol, session=_session)
            hist = ticker.history(period=period, interval="1d", auto_adjust=False)
            if hist.empty:
                logger.warning(f"No history returned for {symbol} (attempt {attempt + 1}/{max_retries})")
                time.sleep(1.5 * (attempt + 1))
                continue
            closes = [float(x) for x in hist["Close"].tolist()]
            dates = [d.strftime("%Y-%m-%d") for d in hist.index.to_pydatetime()]

            name = symbol
            currency = "USD"
            try:
                info = ticker.fast_info
                if hasattr(info, "currency") and info.currency:
                    currency = info.currency
            except Exception:
                pass
            try:
                short_name = ticker.info.get("shortName") or ticker.info.get("longName")
                if short_name:
                    name = short_name
            except Exception:
                pass

            return {
                "symbol": symbol.upper(),
                "name": name,
                "closes": closes,
                "dates": dates,
                "currency": currency,
                "last_price": closes[-1],
            }
        except Exception as e:
            last_err = e
            logger.warning(f"Error fetching {symbol} (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(1.5 * (attempt + 1))
    logger.error(f"Failed to fetch {symbol} after {max_retries} attempts: {last_err}")
    return None


def validate_symbol(symbol: str) -> bool:
    """Check if a ticker symbol is valid by attempting to fetch minimal data."""
    try:
        ticker = yf.Ticker(symbol, session=_session)
        hist = ticker.history(period="5d", interval="1d")
        return not hist.empty
    except Exception:
        return False
