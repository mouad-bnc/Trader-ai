"""Compatibility wrapper for Trader AI portfolio analytics.

The Streamlit app imports :mod:`portfolio_analytics` directly to avoid collisions
with third-party packages named ``analytics`` on hosted environments. This module
keeps older local imports working without duplicating implementation logic.
"""

from __future__ import annotations

from portfolio_analytics import (  # noqa: F401
    Recommendation,
    enrich_portfolio,
    format_money,
    format_pct,
    opportunity_score,
    portfolio_performance_frame,
    recommendation_for,
    triggered_alerts,
)

__all__ = [
    "Recommendation",
    "enrich_portfolio",
    "format_money",
    "format_pct",
    "opportunity_score",
    "portfolio_performance_frame",
    "recommendation_for",
    "triggered_alerts",
]
