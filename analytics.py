"""Portfolio and recommendation calculations for Trader AI."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from coingecko import MarketCoin


@dataclass(frozen=True)
class Recommendation:
    """Human-readable recommendation generated from market and portfolio context."""

    coin_id: str
    symbol: str
    name: str
    opportunity_score: int
    action: str
    rationale: str


def format_money(value: float, currency_symbol: str = "$") -> str:
    return f"{currency_symbol}{value:,.2f}"


def format_pct(value: float) -> str:
    return f"{value:+.2f}%"


def opportunity_score(coin: MarketCoin) -> tuple[int, list[str]]:
    """Score a crypto opportunity from public CoinGecko market fields.

    The score rewards moderate pullbacks, healthy liquidity, and improving short-term
    momentum while penalizing overheated moves and weak volume.
    """

    score = 50
    reasons: list[str] = []

    if -8 <= coin.price_change_24h_pct <= 3:
        score += 12
        reasons.append("24h move is controlled")
    elif coin.price_change_24h_pct > 12:
        score -= 15
        reasons.append("24h move looks overheated")
    elif coin.price_change_24h_pct < -15:
        score -= 10
        reasons.append("sharp 24h drawdown adds risk")

    if coin.price_change_7d_pct > 0:
        score += 10
        reasons.append("7d trend is positive")
    elif -12 <= coin.price_change_7d_pct <= 0:
        score += 5
        reasons.append("7d pullback is still orderly")
    else:
        score -= 8
        reasons.append("7d trend is weak")

    if coin.price_change_30d_pct > 0:
        score += 8
        reasons.append("30d momentum confirms demand")
    elif coin.price_change_30d_pct < -25:
        score -= 8
        reasons.append("30d trend is deeply negative")

    if coin.market_cap_rank and coin.market_cap_rank <= 50:
        score += 8
        reasons.append("large-cap liquidity profile")
    elif coin.market_cap_rank and coin.market_cap_rank <= 150:
        score += 4
        reasons.append("mid-cap liquidity profile")

    volume_to_market_cap = coin.total_volume / coin.market_cap if coin.market_cap else 0
    if volume_to_market_cap >= 0.08:
        score += 8
        reasons.append("strong relative trading volume")
    elif 0 < volume_to_market_cap < 0.015:
        score -= 6
        reasons.append("thin relative volume")

    daily_range = ((coin.high_24h - coin.low_24h) / coin.current_price) * 100 if coin.current_price else 0
    if daily_range > 18:
        score -= 8
        reasons.append("wide intraday range increases risk")
    elif 0 < daily_range <= 8:
        score += 4
        reasons.append("intraday volatility is manageable")

    if coin.ath_change_pct < -70:
        score += 5
        reasons.append("far below all-time high")
    elif coin.ath_change_pct > -10:
        score -= 4
        reasons.append("near all-time high")

    return max(0, min(100, int(score))), reasons[:4]


def recommendation_for(coin: MarketCoin) -> Recommendation:
    score, reasons = opportunity_score(coin)
    if score >= 75:
        action = "Consider accumulating gradually"
    elif score >= 60:
        action = "Watchlist / small position only"
    elif score >= 45:
        action = "Hold or wait for better setup"
    else:
        action = "Avoid new exposure for now"
    rationale = "; ".join(reasons) if reasons else "Neutral market structure from available CoinGecko data"
    return Recommendation(coin.coin_id, coin.symbol, coin.name, score, action, rationale)


def enrich_portfolio(holdings: pd.DataFrame, markets: list[MarketCoin]) -> pd.DataFrame:
    """Attach current CoinGecko prices and P&L metrics to manual holdings."""

    if holdings.empty:
        return pd.DataFrame(columns=["coin_id", "symbol", "quantity", "avg_cost", "current_price", "value", "cost_basis", "pnl", "pnl_pct", "allocation_pct"])

    market_lookup = {coin.coin_id: coin for coin in markets}
    rows: list[dict[str, object]] = []
    for _, holding in holdings.iterrows():
        coin_id = str(holding.get("coin_id", "")).lower().strip()
        coin = market_lookup.get(coin_id)
        quantity = float(holding.get("quantity") or 0)
        avg_cost = float(holding.get("avg_cost") or 0)
        current_price = coin.current_price if coin else 0
        value = quantity * current_price
        cost_basis = quantity * avg_cost
        pnl = value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis else math.nan
        rows.append(
            {
                "coin_id": coin_id,
                "symbol": coin.symbol if coin else coin_id.upper(),
                "name": coin.name if coin else coin_id.title(),
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "value": value,
                "cost_basis": cost_basis,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
            }
        )

    frame = pd.DataFrame(rows)
    total_value = float(frame["value"].sum()) if not frame.empty else 0
    frame["allocation_pct"] = frame["value"].apply(lambda value: (value / total_value * 100) if total_value else 0)
    return frame.sort_values("value", ascending=False)


def portfolio_performance_frame(portfolio: pd.DataFrame, markets: list[MarketCoin]) -> pd.DataFrame:
    """Build an estimated 7-day portfolio value curve from CoinGecko sparklines."""

    if portfolio.empty:
        return pd.DataFrame(columns=["point", "estimated_value"])
    market_lookup = {coin.coin_id: coin for coin in markets}
    max_points = max((len(coin.sparkline) for coin in markets), default=0)
    if max_points == 0:
        return pd.DataFrame(columns=["point", "estimated_value"])
    values = [0.0] * max_points
    for _, holding in portfolio.iterrows():
        coin = market_lookup.get(str(holding.get("coin_id", "")).lower().strip())
        quantity = float(holding.get("quantity") or 0)
        if not coin or not coin.sparkline or quantity <= 0:
            continue
        padded = ([coin.sparkline[0]] * (max_points - len(coin.sparkline))) + coin.sparkline
        values = [current + (price * quantity) for current, price in zip(values, padded)]
    return pd.DataFrame({"point": range(1, max_points + 1), "estimated_value": values})


def triggered_alerts(portfolio: pd.DataFrame, markets: list[MarketCoin]) -> pd.DataFrame:
    """Return rows where current prices cross user-defined alert thresholds."""

    market_lookup = {coin.coin_id: coin for coin in markets}
    alerts: list[dict[str, object]] = []
    for _, holding in portfolio.iterrows():
        coin_id = str(holding.get("coin_id", "")).lower().strip()
        coin = market_lookup.get(coin_id)
        if not coin:
            continue
        below = float(holding.get("alert_below") or 0)
        above = float(holding.get("alert_above") or 0)
        if below > 0 and coin.current_price <= below:
            alerts.append({"Asset": coin.symbol, "Price": coin.current_price, "Alert": f"At or below ${below:,.2f}"})
        if above > 0 and coin.current_price >= above:
            alerts.append({"Asset": coin.symbol, "Price": coin.current_price, "Alert": f"At or above ${above:,.2f}"})
    return pd.DataFrame(alerts)
