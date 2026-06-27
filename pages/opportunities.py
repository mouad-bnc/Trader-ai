from __future__ import annotations

import html

import streamlit as st

from components.ui import render_section_card
from portfolio_analytics import format_money, recommendation_for


def render_opportunities(*, market_objects, confidence_for, coin_logo, score_badge, signal_label) -> None:
    render_section_card("Opportunités", "Analyse indicative uniquement.", notice=True)
    for coin in sorted(market_objects, key=lambda c: recommendation_for(c).opportunity_score, reverse=True)[:12]:
        rec = recommendation_for(coin); conf = confidence_for(coin)
        st.markdown(f"<article class='coin-card'><div class='coin-row'><div class='coin-title'>{coin_logo(coin, coin.symbol)}<div><h3>{coin.name}</h3><p>{coin.symbol}</p></div></div>{score_badge(rec.opportunity_score)}</div><div class='metric-grid'><span>Signal <b>{signal_label(rec.opportunity_score)}</b></span><span>Confiance <b>{conf}%</b></span><span>Prix <b>{format_money(coin.current_price)}</b></span></div><p class='muted'>{html.escape(rec.rationale)}</p></article>", unsafe_allow_html=True)
