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


def _render_kpi_grid(items: list[tuple[str, str, str, str | None]]) -> None:
    cards = []
    for label, value, help_text, delta in items:
        delta_html = f"<span class='home-kpi-delta'>{html.escape(delta)}</span>" if delta else ""
        cards.append(
            "<div class='home-kpi-card'>"
            f"<span>{html.escape(label)}</span>"
            f"<b>{html.escape(value)}</b>"
            f"<small>{html.escape(help_text)}</small>"
            f"{delta_html}"
            "</div>"
        )
    st.markdown(f"<div class='home-kpi-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _watchlist_row_html(asset: MarketAsset) -> str:
    ai_score = score(asset)
    asset_risk = risk(asset)
    confidence_score = confidence(asset)
    signal, dot_class = _signal(ai_score, asset_risk, confidence_score)
    trend_class = "positive" if asset.price_change_24h_pct >= 0 else "negative"
    signal_class = f"signal-{signal.lower()}"
    return (
        "<div class='home-watch-row'>"
        "<div class='watch-left'>"
        f"<span class='status-dot {html.escape(dot_class)}'></span>"
        "<div class='watch-asset'>"
        f"<b>{html.escape(asset.symbol)}</b>"
        f"<small>{html.escape(asset.name)}</small>"
        "</div>"
        "</div>"
        "<div class='watch-right'>"
        "<div class='watch-price'>"
        f"<b>{html.escape(money(asset.current_price))}</b>"
        f"<small class='{trend_class}'>{html.escape(percent(asset.price_change_24h_pct))}</small>"
        "</div>"
        "<div class='watch-chips'>"
        f"<span>IA {html.escape(percent_score(ai_score))}</span>"
        f"<span class='{html.escape(signal_class)}'>{html.escape(signal)}</span>"
        "</div>"
        "</div>"
        "</div>"
    )


def _render_watchlist(markets: list[MarketAsset], market_trend: str) -> None:
    rows = "".join(_watchlist_row_html(asset) for asset in markets[:5])
    body = rows or "<p class='muted'>Watchlist indisponible.</p>"
    st.markdown(
        "<section class='home-watch-card'>"
        "<div class='home-watch-head'>"
        "<div><span class='pill soft'>Watchlist</span><h2>Top 5 actifs</h2></div>"
        f"<div class='home-trend'><span>Tendance</span><b>{html.escape(market_trend)}</b></div>"
        "</div>"
        f"<div class='home-watch-list'>{body}</div>"
        "</section>",
        unsafe_allow_html=True,
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
    portfolio_message = "Total réel Binance Spot" if has_binance_positions else "Connectez Binance en lecture seule ou vérifiez que votre portefeuille Spot contient des actifs."
    avg_24h = sum(asset.price_change_24h_pct for asset in markets) / len(markets) if markets else 0
    ranked_opportunities = sorted(markets, key=score, reverse=True)[:3]
    avg_risk = sum(risk(asset) for asset in markets) / len(markets) if markets else 0
    avg_confidence = sum(confidence(asset) for asset in markets) / len(markets) if markets else 0
    top_opportunity = ranked_opportunities[0] if ranked_opportunities else None

    top_symbol = top_opportunity.symbol if top_opportunity else "—"
    top_caption = top_opportunity.name if top_opportunity else "Aucune opportunité détectée"
    market_trend = percent(avg_24h)
    fear_value = f"{fear.value}%" if fear.value is not None else "—"
    btc_dominance = f"{metrics.get('btc_dominance', 0):.1f}%"

    with st.container():
        st.caption(APP_SUBTITLE)
        st.title(HOME_TITLE)
        st.caption(HOME_SUBTITLE)

    _render_kpi_grid(
        [
            ("Portfolio", portfolio_label, portfolio_message, None),
            ("P&L 24h", money(daily_pnl, "USDT"), "Binance Spot", None),
            ("Risque", f"{avg_risk:.0f}%", "Score agrégé", None),
            ("Confiance", f"{avg_confidence:.0f}%", "Qualité données", None),
            ("Tendance marché", market_trend, "Moyenne watchlist", None),
            ("Fear & Greed", fear_value, fear.label, None),
            ("Top opportunité", top_symbol, top_caption, None),
            ("Dominance BTC", btc_dominance, "Marché global", None),
        ]
    )
    _render_watchlist(markets, market_trend)
    if not markets:
        empty_state("Données marché indisponibles", "Aucune donnée live n'a pu être chargée. Les pages restent accessibles avec des états vides élégants.")
