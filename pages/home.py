from __future__ import annotations

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


def _render_kpi(label: str, value: str, help_text: str, delta: str | None = None) -> None:
    with st.container(border=True):
        st.metric(label=label, value=value, delta=delta, help=help_text)
        st.caption(help_text)


def _render_watchlist_row(asset: MarketAsset) -> None:
    ai_score = score(asset)
    asset_risk = risk(asset)
    confidence_score = confidence(asset)
    signal, _ = _signal(ai_score, asset_risk, confidence_score)
    trend = percent(asset.price_change_24h_pct)
    cols = st.columns([0.9, 1.4, 1, 1, 0.9], vertical_alignment="center")
    cols[0].markdown(f"**{asset.symbol}**")
    cols[1].caption(asset.name)
    cols[2].markdown(money(asset.current_price))
    cols[3].metric("24h", trend)
    cols[4].metric("Score IA", percent_score(ai_score))
    st.caption(f"Signal : {signal}")


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

    kpi_rows = [
        [
            ("Portfolio", portfolio_label, portfolio_message, None),
            ("P&L 24h", money(daily_pnl, "USDT"), "Binance Spot", None),
            ("Risque", f"{avg_risk:.0f}%", "Score agrégé", None),
            ("Confiance", f"{avg_confidence:.0f}%", "Qualité données", None),
        ],
        [
            ("Tendance marché", market_trend, "Moyenne watchlist", None),
            ("Fear & Greed", fear_value, fear.label, None),
            ("Top opportunité", top_symbol, top_caption, None),
            ("Dominance BTC", btc_dominance, "Marché global", None),
        ],
    ]
    for row in kpi_rows:
        for column, (label, value, help_text, delta) in zip(st.columns(4), row, strict=True):
            with column:
                _render_kpi(label, value, help_text, delta)

    with st.container(border=True):
        title_col, trend_col = st.columns([3, 1], vertical_alignment="center")
        title_col.subheader("Watchlist · Top 5 actifs")
        trend_col.metric("Tendance", market_trend)
        if markets:
            header = st.columns([0.9, 1.4, 1, 1, 0.9], vertical_alignment="center")
            for col, label in zip(header, ["Symbole", "Actif", "Prix", "24h", "IA"], strict=True):
                col.caption(label)
            for asset in markets[:5]:
                _render_watchlist_row(asset)
        else:
            st.caption("Watchlist indisponible.")
    if not markets:
        empty_state("Données marché indisponibles", "Aucune donnée live n'a pu être chargée. Les pages restent accessibles avec des états vides élégants.")
