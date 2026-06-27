from __future__ import annotations

import streamlit as st


def render_markets(*, market_objects, fng_display: str, dominance: float, render_market_card) -> None:
    st.markdown(f"<section class='glass-card'><div class='section-head'><h2>Marchés</h2><span class='muted'>Fear & Greed {fng_display} · BTC {dominance:.1f}%</span></div></section>", unsafe_allow_html=True)
    query = st.text_input("Recherche crypto", placeholder="BTC, ETH, SOL…")
    filtered = [c for c in market_objects if not query or query.lower() in c.name.lower() or query.upper() in c.symbol]
    st.markdown("<h3>Meilleures hausses</h3>", unsafe_allow_html=True)
    for coin in sorted(filtered, key=lambda c: c.price_change_24h_pct, reverse=True)[:3]: render_market_card(coin, favorite=coin.coin_id in st.session_state.watchlist)
    st.markdown("<h3>Plus fortes baisses</h3>", unsafe_allow_html=True)
    for coin in sorted(filtered, key=lambda c: c.price_change_24h_pct)[:3]: render_market_card(coin, favorite=coin.coin_id in st.session_state.watchlist)
    st.markdown("<h3>Liste de suivi</h3>", unsafe_allow_html=True)
    for coin in [c for c in filtered if c.coin_id in st.session_state.watchlist][:5]: render_market_card(coin, favorite=True)
