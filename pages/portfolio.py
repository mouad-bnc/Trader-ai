from __future__ import annotations

import streamlit as st
from components.charts import allocation_bar
from components.cards import empty_state
from services.binance_service import BinanceService
from services.coingecko_service import CoinGeckoService
from services.portfolio_service import PortfolioService
from utils.helpers import money, percent


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]; pf = services["portfolio"]; bz = services["binance"]
    assert isinstance(cg, CoinGeckoService) and isinstance(pf, PortfolioService) and isinstance(bz, BinanceService)
    st.title("Portefeuille")
    markets = cg.get_markets()
    summary = pf.summarize(pf.demo_holdings(), markets)
    st.markdown(f"<div class='card hero'><span class='pill'>Lecture seule</span><h2>{money(summary.total_value)}</h2><p class='{ 'positive' if summary.pnl >= 0 else 'negative' }'>{money(summary.pnl)} · {percent(summary.pnl_pct)}</p></div>", unsafe_allow_html=True)
    if not summary.positions:
        empty_state("Aucune position", "Connectez Binance en lecture seule ou importez vos positions plus tard.")
    for pos in summary.positions:
        st.markdown(f"<div class='card'><div class='row'><div><h3>{pos.holding.name}</h3><p class='muted'>{pos.holding.quantity:g} {pos.holding.symbol}</p></div><div style='text-align:right'><b>{money(pos.value)}</b><p class='{ 'positive' if pos.pnl >= 0 else 'negative' }'>{percent(pos.pnl_pct)}</p></div></div></div>", unsafe_allow_html=True)
    allocation_bar(pf.allocation(summary))
    balances = bz.account_snapshot()
    if not bz.configured:
        empty_state("Binance non configuré", "Ajoutez des clés API en lecture seule dans les secrets Streamlit. Aucun ordre de trading n'est implémenté.")
    elif not balances:
        empty_state("Synchronisation Binance vide", "La connexion est protégée et n'a retourné aucun solde exploitable.")
