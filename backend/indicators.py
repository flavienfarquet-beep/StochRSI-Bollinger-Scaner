"""Technical indicator calculations: RSI, SMA, MA crossovers."""
from __future__ import annotations

from typing import List, Optional


def sma(values: List[float], period: int) -> List[Optional[float]]:
    """Simple Moving Average. Returns list aligned with values; first period-1 entries are None."""
    out: List[Optional[float]] = []
    if period <= 0 or not values:
        return [None] * len(values)
    cumulative = 0.0
    for i, v in enumerate(values):
        cumulative += v
        if i >= period:
            cumulative -= values[i - period]
        out.append(cumulative / period if i >= period - 1 else None)
    return out


def ema(values: List[float], period: int) -> List[Optional[float]]:
    """Exponential Moving Average. Seeded with SMA of first `period` values."""
    n = len(values)
    out: List[Optional[float]] = [None] * n
    if period <= 0 or n < period:
        return out
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    k = 2 / (period + 1)
    prev = seed
    for i in range(period, n):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def moving_average(values: List[float], period: int, ma_type: str = "sma") -> List[Optional[float]]:
    return ema(values, period) if ma_type == "ema" else sma(values, period)


def rsi(values: List[float], period: int = 14) -> List[Optional[float]]:
    """Wilder's RSI. Returns list aligned with values; entries before enough data are None."""
    n = len(values)
    out: List[Optional[float]] = [None] * n
    if n <= period or period <= 0:
        return out

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        if change >= 0:
            gains += change
        else:
            losses -= change

    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = _rsi_from_avg(avg_gain, avg_loss)

    for i in range(period + 1, n):
        change = values[i] - values[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = _rsi_from_avg(avg_gain, avg_loss)

    return out


def _rsi_from_avg(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def detect_crossover(short_ma: List[Optional[float]], long_ma: List[Optional[float]]) -> Optional[str]:
    """Detect golden_cross / death_cross on the most recent bar. Returns 'golden_cross', 'death_cross' or None."""
    n = len(short_ma)
    if n < 2:
        return None
    s_now, s_prev = short_ma[-1], short_ma[-2]
    l_now, l_prev = long_ma[-1], long_ma[-2]
    if None in (s_now, s_prev, l_now, l_prev):
        return None
    if s_prev <= l_prev and s_now > l_now:
        return "golden_cross"
    if s_prev >= l_prev and s_now < l_now:
        return "death_cross"
    return None


def ma_position(short_ma: List[Optional[float]], long_ma: List[Optional[float]]) -> Optional[str]:
    """Return 'above' if short MA > long MA on the last bar, 'below' if short MA < long MA, else None."""
    if not short_ma or not long_ma:
        return None
    s, l = short_ma[-1], long_ma[-1]
    if s is None or l is None:
        return None
    if s > l:
        return "above"
    if s < l:
        return "below"
    return "equal"


def rsi_signal(value: Optional[float], lower: float, upper: float) -> Optional[str]:
    if value is None:
        return None
    if value <= lower:
        return "oversold"
    if value >= upper:
        return "overbought"
    return None
