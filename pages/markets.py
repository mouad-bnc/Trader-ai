from __future__ import annotations

import streamlit as st
from components.cards import asset_card, empty_state
from services.coingecko_service import CoinGeckoService


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]
    assert isinstance(cg, CoinGeckoService)
    st.title("Marchés")
    markets = cg.get_markets()
    gainers, losers = cg.top_gainers_losers(markets)
    metrics = cg.global_metrics()
    st.markdown(f"<div class='card'><div class='metric'><div><span class='muted'>Dominance BTC</span><b>{metrics.get('btc_dominance',0):.1f}%</b></div><div><span class='muted'>Marché 24h</span><b>{metrics.get('market_cap_change_24h',0):+.2f}%</b></div><div><span class='muted'>Watchlist</span><b>{len(markets)}</b></div></div></div>", unsafe_allow_html=True)
    if not markets:
        empty_state("Marchés hors ligne", "CoinGecko est indisponible ou limité. Réessayez plus tard.")
        return
    tab1, tab2, tab3 = st.tabs(["Tous", "Gagnants", "Perdants"])
    with tab1:
        for asset in markets:
            asset_card(asset)
    with tab2:
        for asset in gainers:
            asset_card(asset)
    with tab3:
        for asset in losers:
            asset_card(asset)
