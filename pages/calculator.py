from __future__ import annotations

import streamlit as st

from portfolio_analytics import format_money, format_pct


def render_calculator(*, pct_class) -> None:
    st.markdown("<section class='glass-card'><h2>Calculateur</h2><p class='muted'>Résultat instantané.</p></section>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    capital = c1.number_input("Capital", min_value=0.0, value=1000.0)
    prix = c2.number_input("Prix actuel", min_value=0.000001, value=100.0, format="%.6f")
    entree = c1.number_input("Prix d’entrée", min_value=0.000001, value=90.0, format="%.6f")
    sortie = c2.number_input("Objectif gain", min_value=0.000001, value=120.0, format="%.6f")
    stop = c1.number_input("Seuil de protection", min_value=0.000001, value=80.0, format="%.6f")
    dca = c2.number_input("Achat DCA", min_value=0.0, value=250.0)
    qty = capital / entree if entree else 0
    avg = (capital + dca) / (qty + dca / prix) if prix and qty + dca / prix else entree
    roi = (sortie - avg) / avg * 100
    risk = max(avg - stop, 0); reward = max(sortie - avg, 0)
    st.markdown(f"<section class='portfolio-card'><div class='metric-grid'><span>Prix moyen <b>{format_money(avg)}</b></span><span>DCA <b>{format_money(dca)}</b></span><span>ROI <b class='{pct_class(roi)}'>{format_pct(roi)}</b></span><span>Ratio risque/rendement <b>{(reward/risk if risk else 0):.2f}</b></span><span>Taille position <b>{qty:.6f}</b></span><span>Seuil de protection <b>{format_money(stop)}</b></span></div></section>", unsafe_allow_html=True)
