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


def _watchlist_row(asset: MarketAsset) -> str:
    ai_score = score(asset)
    asset_risk = risk(asset)
    confidence_score = confidence(asset)
    signal, dot_class = _signal(ai_score, asset_risk, confidence_score)
    trend_class = "positive" if asset.price_change_24h_pct >= 0 else "negative"
    return (
        "<div class='home-watch-row'>"
        f"<span class='status-dot {dot_class}'></span>"
        f"<b>{html.escape(asset.symbol)}</b>"
        f"<span>{money(asset.current_price)}</span>"
        f"<span class='{trend_class}'>{percent(asset.price_change_24h_pct)}</span>"
        f"<span>{percent_score(ai_score)}</span>"
        f"<span class='home-signal {dot_class}'>{signal}</span>"
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
    daily_pnl = binance_summary.pnl_24h_usdt if has_binance_positions and binance_summary and binance_summary.pnl_24h_usdt else 0
    daily_pnl_class = "positive" if daily_pnl >= 0 else "negative"
    portfolio_message = "Total réel Binance Spot" if has_binance_positions else "Connectez Binance en lecture seule ou vérifiez que votre portefeuille Spot contient des actifs."
    avg_24h = sum(asset.price_change_24h_pct for asset in markets) / len(markets) if markets else 0
    ranked_opportunities = sorted(markets, key=score, reverse=True)[:3]
    avg_risk = sum(risk(asset) for asset in markets) / len(markets) if markets else 0
    avg_confidence = sum(confidence(asset) for asset in markets) / len(markets) if markets else 0
    top_opportunity = ranked_opportunities[0] if ranked_opportunities else None
    market_class = "positive" if avg_24h >= 0 else "negative"

    top_symbol = html.escape(top_opportunity.symbol if top_opportunity else "—")
    top_caption = html.escape(top_opportunity.name if top_opportunity else "Aucune opportunité détectée")
    watchlist_rows = "".join(_watchlist_row(asset) for asset in markets[:5]) or "<p class='muted'>Watchlist indisponible.</p>"

    st.markdown(
        f"""
        <div class='home-cockpit'>
            <section class='home-cockpit-head'>
                <div>
                    <span class='pill'>{APP_SUBTITLE}</span>
                    <h1>{HOME_TITLE}</h1>
                </div>
                <p class='muted'>{HOME_SUBTITLE}</p>
            </section>

            <section class='home-kpi-grid' aria-label='Trading cockpit KPIs'>
                <div class='home-kpi'><span>Portfolio</span><b>{portfolio_label}</b><small>{html.escape(portfolio_message)}</small></div>
                <div class='home-kpi'><span>P&amp;L 24h</span><b class='{daily_pnl_class}'>{money(daily_pnl, 'USDT')}</b><small>Binance Spot</small></div>
                <div class='home-kpi'><span>Risk</span><b>{avg_risk:.0f}%</b><small>Score agrégé</small></div>
                <div class='home-kpi'><span>Confidence</span><b>{avg_confidence:.0f}%</b><small>Qualité données</small></div>
                <div class='home-kpi'><span>Market Trend</span><b class='{market_class}'>{percent(avg_24h)}</b><small>Moyenne watchlist</small></div>
                <div class='home-kpi'><span>Fear &amp; Greed</span><b>{fear.value if fear.value is not None else '—'}%</b><small>{html.escape(fear.label)}</small></div>
                <div class='home-kpi home-kpi-opportunity'><span>Top Opportunity</span><b>{top_symbol}</b><small>{top_caption}</small></div>
                <div class='home-kpi'><span>BTC Dominance</span><b>{metrics.get('btc_dominance',0):.1f}%</b><small>Marché global</small></div>
            </section>

            <section class='home-watch-card' aria-label='Compact watchlist'>
                <div class='home-watch-title'>
                    <div><span class='pill soft'>Watchlist</span><h3>Top 5 actifs</h3></div>
                    <b class='{market_class}'>{percent(avg_24h)}</b>
                </div>
                <div class='home-watch-head'>
                    <span></span><span>Symbol</span><span>Price</span><span>24h %</span><span>AI Score</span><span>Signal</span>
                </div>
                <div class='home-watch-list'>{watchlist_rows}</div>
            </section>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not markets:
        empty_state("Données marché indisponibles", "Aucune donnée live n'a pu être chargée. Les pages restent accessibles avec des états vides élégants.")
