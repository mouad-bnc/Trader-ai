from __future__ import annotations

import html

import streamlit as st
from components.cards import empty_state
from pages.opportunities import confidence, percent_score, risk, score
from services.binance_service import BinanceService
from services.coingecko_service import CoinGeckoService, MarketAsset
from utils.constants import APP_SUBTITLE, HOME_SUBTITLE, HOME_TITLE
from utils.helpers import money, percent


def _signal(ai_score: float, asset_risk: float, confidence_score: float) -> tuple[str, str]:
    if asset_risk >= 68 or ai_score < 42:
        return "Sell", "dot-sell"
    if ai_score >= 70 and asset_risk < 52 and confidence_score >= 58:
        return "Buy", "dot-buy"
    return "Wait", "dot-wait"


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _watchlist_row(asset: MarketAsset) -> str:
    ai_score = score(asset)
    asset_risk = risk(asset)
    confidence_score = confidence(asset)
    signal, dot_class = _signal(ai_score, asset_risk, confidence_score)
    trend_class = "positive" if asset.price_change_24h_pct >= 0 else "negative"
    return (
        "<div class='home-watch-row'>"
        f"<span class='status-dot {dot_class}'></span>"
        f"<b>{_escape(asset.symbol)}</b>"
        f"<span>{_escape(money(asset.current_price))}</span>"
        f"<span class='{trend_class}'>{_escape(percent(asset.price_change_24h_pct))}</span>"
        f"<span>{_escape(percent_score(ai_score))}</span>"
        f"<span class='home-signal {dot_class}'>{_escape(signal)}</span>"
        "</div>"
    )


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]
    bz = services["binance"]
    assert isinstance(cg, CoinGeckoService) and isinstance(bz, BinanceService)
    markets = cg.get_markets()
    metrics = cg.global_metrics()
    fear = cg.fear_greed()
    binance_summary = bz.spot_portfolio(cg) if bz.configured else None
    has_binance_positions = bool(binance_summary and binance_summary.connected and binance_summary.positions)
    portfolio_label = money(binance_summary.total_value_usdt, "USDT") if has_binance_positions else "Indisponible"
    safe_portfolio_label = _escape(portfolio_label)
    daily_pnl = binance_summary.pnl_24h_usdt if has_binance_positions and binance_summary and binance_summary.pnl_24h_usdt else 0
    daily_pnl_class = "positive" if daily_pnl >= 0 else "negative"
    portfolio_message = "Total réel Binance Spot" if has_binance_positions else "Connectez Binance en lecture seule ou vérifiez que votre portefeuille Spot contient des actifs."
    avg_24h = sum(asset.price_change_24h_pct for asset in markets) / len(markets) if markets else 0
    ranked_opportunities = sorted(markets, key=score, reverse=True)[:3]
    avg_risk = sum(risk(asset) for asset in markets) / len(markets) if markets else 0
    avg_confidence = sum(confidence(asset) for asset in markets) / len(markets) if markets else 0
    top_opportunity = ranked_opportunities[0] if ranked_opportunities else None
    market_class = "positive" if avg_24h >= 0 else "negative"

    top_symbol = _escape(top_opportunity.symbol if top_opportunity else "—")
    top_caption = _escape(top_opportunity.name if top_opportunity else "Aucune opportunité détectée")
    watchlist_rows = "".join(_watchlist_row(asset) for asset in markets[:5]) or "<p class='muted'>Watchlist indisponible.</p>"
    safe_app_subtitle = _escape(APP_SUBTITLE)
    safe_home_title = _escape(HOME_TITLE)
    safe_home_subtitle = _escape(HOME_SUBTITLE)
    safe_portfolio_message = _escape(portfolio_message)
    safe_daily_pnl = _escape(money(daily_pnl, "USDT"))
    safe_market_trend = _escape(percent(avg_24h))
    safe_fear_value = _escape(f"{fear.value}%" if fear.value is not None else "—")
    safe_fear_label = _escape(fear.label)
    safe_btc_dominance = _escape(f"{metrics.get('btc_dominance', 0):.1f}%")

    cockpit_html = f"""
        <div class='home-cockpit'>
            <section class='home-cockpit-head'>
                <div>
                    <span class='pill'>{safe_app_subtitle}</span>
                    <h1>{safe_home_title}</h1>
                </div>
                <p class='muted'>{safe_home_subtitle}</p>
            </section>

            <section class='home-kpi-grid' aria-label='Trading cockpit KPIs'>
                <div class='home-kpi'><span>Portfolio</span><b>{safe_portfolio_label}</b><small>{safe_portfolio_message}</small></div>
                <div class='home-kpi'><span>P&amp;L 24h</span><b class='{daily_pnl_class}'>{safe_daily_pnl}</b><small>Binance Spot</small></div>
                <div class='home-kpi'><span>Risk</span><b>{avg_risk:.0f}%</b><small>Score agrégé</small></div>
                <div class='home-kpi'><span>Confidence</span><b>{avg_confidence:.0f}%</b><small>Qualité données</small></div>
                <div class='home-kpi'><span>Market Trend</span><b class='{market_class}'>{safe_market_trend}</b><small>Moyenne watchlist</small></div>
                <div class='home-kpi'><span>Fear &amp; Greed</span><b>{safe_fear_value}</b><small>{safe_fear_label}</small></div>
                <div class='home-kpi home-kpi-opportunity'><span>Top Opportunity</span><b>{top_symbol}</b><small>{top_caption}</small></div>
                <div class='home-kpi'><span>BTC Dominance</span><b>{safe_btc_dominance}</b><small>Marché global</small></div>
            </section>

            <section class='home-watch-card' aria-label='Compact watchlist'>
                <div class='home-watch-title'>
                    <div><span class='pill soft'>Watchlist</span><h3>Top 5 actifs</h3></div>
                    <b class='{market_class}'>{safe_market_trend}</b>
                </div>
                <div class='home-watch-head'>
                    <span></span><span>Symbol</span><span>Price</span><span>24h %</span><span>AI Score</span><span>Signal</span>
                </div>
                <div class='home-watch-list'>{watchlist_rows}</div>
            </section>
        </div>
        """
    st.markdown(cockpit_html, unsafe_allow_html=True)
    if not markets:
        empty_state("Données marché indisponibles", "Aucune donnée live n'a pu être chargée. Les pages restent accessibles avec des états vides élégants.")
