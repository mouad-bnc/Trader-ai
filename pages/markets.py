from __future__ import annotations

import html

import streamlit as st
from components.cards import asset_card_html, empty_state
from components.charts import range_chart
from services.coingecko_service import CoinGeckoService


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]
    assert isinstance(cg, CoinGeckoService)
    st.markdown("<div class='dashboard-micro-title'><div><span class='pill'>Marchés</span><h1>Marchés</h1></div><span class='muted'>Vue compacte multi-actifs</span></div>", unsafe_allow_html=True)
    markets = cg.get_markets()
    gainers, losers = cg.top_gainers_losers(markets)
    _render_watchlist_ui(markets)
    metrics = cg.global_metrics()
    st.markdown(f"<div class='cockpit-card-sm'><div class='metric'><div><span class='muted'>Dominance BTC</span><b>{metrics.get('btc_dominance',0):.1f}%</b></div><div><span class='muted'>Marché 24h</span><b>{metrics.get('market_cap_change_24h',0):+.2f}%</b></div><div><span class='muted'>Watchlist</span><b>{len(markets)}</b></div></div></div>", unsafe_allow_html=True)
    if not markets:
        empty_state("Marchés hors ligne", "CoinGecko est indisponible ou limité. Réessayez plus tard.")
        return
    tab1, tab2, tab3 = st.tabs(["Tous", "Gagnants", "Perdants"])
    with tab1:
        ranges = {"24H": 1, "7D": 7, "30D": 30, "90D": 90, "1Y": 365}
        selected_range = st.radio("Plage graphique", list(ranges), horizontal=True)
        focus = markets[0] if markets else None
        if focus:
            values = focus.sparkline if selected_range == "7D" and len(focus.sparkline) > 1 else cg.history(focus.id, ranges[selected_range])
            range_chart(f"Graphique compact {focus.name}", values, selected_range)
        else:
            empty_state("Graphique indisponible", "Données insuffisantes pour afficher ce graphique.")
        st.markdown("<div class='market-grid'>" + "".join(asset_card_html(asset) for asset in markets) + "</div>", unsafe_allow_html=True)
    with tab2:
        st.markdown("<div class='market-grid'>" + "".join(asset_card_html(asset) for asset in gainers) + "</div>", unsafe_allow_html=True)
    with tab3:
        st.markdown("<div class='market-grid'>" + "".join(asset_card_html(asset) for asset in losers) + "</div>", unsafe_allow_html=True)


def _render_watchlist_ui(markets) -> None:
    defaults = [asset.symbol for asset in markets[:4]] or ["BTC", "ETH"]
    if "watchlist_symbols" not in st.session_state:
        st.session_state.watchlist_symbols = defaults
    if "watchlist_favorites" not in st.session_state:
        st.session_state.watchlist_favorites = []
    with st.expander("Watchlist UI", expanded=False):
        new_asset = st.text_input("Ajouter un actif", placeholder="Ex: BTC")
        if st.button("Ajouter à la watchlist") and new_asset.strip():
            symbol = new_asset.strip().upper()
            if symbol not in st.session_state.watchlist_symbols:
                st.session_state.watchlist_symbols.append(symbol)
        for symbol in list(st.session_state.watchlist_symbols):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
            col1.markdown(f"**{html.escape(symbol)}**")
            if col2.button("★ Favori", key=f"fav_{symbol}") and symbol not in st.session_state.watchlist_favorites:
                st.session_state.watchlist_favorites.append(symbol)
            if col3.button("Retirer", key=f"rm_{symbol}"):
                st.session_state.watchlist_symbols.remove(symbol)
            col4.text_input("Alerte prix", key=f"alert_{symbol}", placeholder="UI uniquement")
        st.caption("Aucune notification réelle et aucun job de fond ne sont activés pour le moment.")
