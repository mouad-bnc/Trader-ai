from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def money(value: float | None, currency: str = "USD") -> str:
    amount = safe_float(value)
    symbol = "$" if currency.upper() == "USD" else f"{currency.upper()} "
    if abs(amount) >= 1_000_000_000:
        return f"{symbol}{amount/1_000_000_000:.2f}B"
    if abs(amount) >= 1_000_000:
        return f"{symbol}{amount/1_000_000:.2f}M"
    if abs(amount) >= 1_000:
        return f"{symbol}{amount:,.2f}"
    if abs(amount) >= 1:
        return f"{symbol}{amount:,.2f}"
    return f"{symbol}{amount:,.6f}"


def percent(value: float | None) -> str:
    return f"{safe_float(value):+.2f}%"


def now_utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))
