from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from binance import BinanceReadOnlyClient
from components.ui import render_empty_card
from portfolio_analytics import format_money, format_pct
from portfolio_io import normalize_portfolio


def render_portfolio(*, portfolio, total_value: float, total_pnl: float, total_pnl_pct: float, market_ids, market_lookup, pct_class, render_holding_card) -> None:
    binance = BinanceReadOnlyClient()
    if portfolio.empty:
        render_empty_card("◒", "Votre portefeuille est prêt.", "Connectez Binance ou ajoutez une position pour afficher la valeur totale, l'allocation, le donut et la liste des actifs.")
    else:
        st.markdown(f"<section class='portfolio-card'><span class='eyebrow'>PORTEFEUILLE</span><div class='value'>{format_money(total_value)}</div><div class='donut'></div><div class='quick-grid'><div class='mini-stat'><span>Spot</span><b>{format_money(total_value)}</b></div><div class='mini-stat'><span>Allocation</span><b>{len(portfolio)} actifs</b></div><div class='mini-stat'><span>PnL</span><b class='{pct_class(total_pnl)}'>{format_pct(total_pnl_pct)}</b></div></div></section>", unsafe_allow_html=True)
    if not binance.configured:
        render_empty_card("", "Binance", "API absente. Activez une clé lecture seule pour synchroniser automatiquement vos soldes Spot.", section_head=True, badge="Hors ligne")
        st.button("Connecter Binance", use_container_width=True)
    else:
        try:
            assets = binance.spot_assets()
            st.markdown("<h3>Binance Spot lecture seule</h3>", unsafe_allow_html=True)
            for asset in assets[:12]:
                st.markdown(f"<div class='glass-card'><div class='metric-line'><b>{asset.symbol}</b><span>{asset.quantity:,.8f}</span></div><div class='metric-line'><span>Prix actuel</span><b>{format_money(asset.current_price)}</b></div><div class='metric-line'><span>Valeur</span><b>{format_money(asset.value)}</b></div></div>", unsafe_allow_html=True)
        except Exception as exc:
            st.warning(f"Lecture Binance indisponible : {html.escape(str(exc))}")
    with st.expander("Ajouter ou modifier une position", expanded=portfolio.empty):
        with st.form("holding_form", clear_on_submit=False):
            coin_id = st.selectbox("Actif", options=market_ids, format_func=lambda cid: f"{market_lookup[cid].name} ({market_lookup[cid].symbol})")
            quantity = st.number_input("Quantité", min_value=0.0, step=0.0001, format="%.8f")
            avg_cost = st.number_input("Prix moyen", min_value=0.0, step=1.0, format="%.4f")
            favorite = st.toggle("Favori", value=True)
            if st.form_submit_button("Enregistrer la position", use_container_width=True):
                coin = market_lookup[coin_id]
                next_row = pd.DataFrame([{"coin_id": coin_id, "symbol": coin.symbol, "quantity": quantity, "avg_cost": avg_cost, "alert_below": 0, "alert_above": 0, "favorite": favorite, "notes": ""}])
                st.session_state.portfolio = normalize_portfolio(pd.concat([st.session_state.portfolio[st.session_state.portfolio["coin_id"] != coin_id], next_row], ignore_index=True)); st.rerun()
    for _, row in portfolio.iterrows(): render_holding_card(row, market_lookup.get(str(row['coin_id'])))
