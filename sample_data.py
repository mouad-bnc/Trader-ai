"""Legacy compatibility exports for Trader AI."""

from __future__ import annotations

from portfolio_io import empty_portfolio


def default_portfolio():
    """Return an empty real portfolio instead of demo holdings."""

    return empty_portfolio()
