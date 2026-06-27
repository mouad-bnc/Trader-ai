from __future__ import annotations

import html
from datetime import datetime

import pandas as pd
import streamlit as st

from components.ui import render_empty_card
from portfolio_analytics import format_money, format_pct


def render_portfolio(*, portfolio, total_value: float, total_pnl: float, total_pnl_pct: float, market_ids, market_lookup, pct_class, render_holding_card, portfolio_service, connection_status: str, connection_message: str, last_sync: str | None) -> None:
    if portfolio.empty:
        render_empty_card("◒", "Votre portefeuille est prêt.", "Connectez Binance ou ajoutez une position pour afficher la valeur totale, l'allocation, le donut et la liste des actifs.")
    else:
        st.markdown(f"<section class='portfolio-card'><span class='eyebrow'>PORTEFEUILLE</span><div class='value'>{format_money(total_value)}</div><div class='donut'></div><div class='quick-grid'><div class='mini-stat'><span>Spot</span><b>{format_money(total_value)}</b></div><div class='mini-stat'><span>Allocation</span><b>{len(portfolio)} actifs</b></div><div class='mini-stat'><span>PnL</span><b class='{pct_class(total_pnl)}'>{format_pct(total_pnl_pct)}</b></div></div></section>", unsafe_allow_html=True)
    if connection_status == "connected":
        sync_label = _format_sync_date(last_sync)
        render_empty_card("", "Binance connecté", f"Synchronisation automatique active. Dernière synchronisation : {sync_label}.", section_head=True, badge="En ligne")
    elif connection_status == "not_configured":
        render_empty_card("", "Connexion Binance non configurée", "Ajoutez une clé Binance lecture seule côté serveur pour synchroniser automatiquement vos soldes Spot.", section_head=True, badge="Hors ligne")
        st.button("Connecter Binance", use_container_width=True)
    elif connection_status == "imported_csv":
        render_empty_card("", "Portefeuille importé", connection_message, section_head=True, badge="CSV")
    else:
        render_empty_card("", "Synchronisation Binance indisponible", html.escape(connection_message), section_head=True, badge="Attention")
    if not market_ids:
        render_empty_card("◌", "Données marché indisponibles", "Impossible d’ajouter ou modifier une position tant que les données marché sont absentes.")
    else:
        with st.expander("Ajouter ou modifier une position", expanded=portfolio.empty):
            with st.form("holding_form", clear_on_submit=False):
                coin_id = st.selectbox("Actif", options=market_ids, format_func=lambda cid: f"{market_lookup[cid].name} ({market_lookup[cid].symbol})")
                quantity = st.number_input("Quantité", min_value=0.0, step=0.0001, format="%.8f")
                avg_cost = st.number_input("Prix moyen", min_value=0.0, step=1.0, format="%.4f")
                favorite = st.toggle("Favori", value=True)
                if st.form_submit_button("Enregistrer la position", use_container_width=True):
                    coin = market_lookup[coin_id]
                    next_row = pd.DataFrame([{"coin_id": coin_id, "symbol": coin.symbol, "quantity": quantity, "avg_cost": avg_cost, "alert_below": 0, "alert_above": 0, "favorite": favorite, "notes": ""}])
                    st.session_state.portfolio = portfolio_service.load(pd.concat([st.session_state.portfolio[st.session_state.portfolio["coin_id"] != coin_id], next_row], ignore_index=True)); st.rerun()
    for _, row in portfolio.iterrows(): render_holding_card(row, market_lookup.get(str(row['coin_id'])))


def _format_sync_date(value: str | None) -> str:
    if not value:
        return "non disponible"
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y %H:%M UTC")
    except ValueError:
        return "non disponible"
