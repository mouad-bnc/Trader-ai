from __future__ import annotations
import streamlit as st
from services.coingecko_service import CoinGeckoService
from services.portfolio_service import PortfolioService
from utils.helpers import money, percent


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]; pf = services["portfolio"]
    assert isinstance(cg, CoinGeckoService) and isinstance(pf, PortfolioService)
    st.title("Trader IA")
    markets = cg.get_markets()
    summary = pf.summarize(pf.demo_holdings(), markets)
    st.markdown("<div class='card'><span class='pill'>Assistant contextuel</span><p class='muted'>Posez une question sur le portefeuille, le marché ou le risque. Les réponses restent éducatives.</p></div>", unsafe_allow_html=True)
    prompt = st.text_input("Votre question", placeholder="Analyse mon portefeuille")
    if not prompt:
        st.markdown("<div class='card'><b>Suggestions rapides</b><p class='muted'>Analyse portefeuille · Risque BTC · Opportunités · Résumé marché</p></div>", unsafe_allow_html=True)
        return
    response = f"Portefeuille estimé à {money(summary.total_value)} avec un PnL de {percent(summary.pnl_pct)}. "
    if markets:
        best = max(markets, key=lambda a: a.price_change_24h_pct)
        response += f"Le meilleur momentum 24h de la watchlist est {best.name} ({percent(best.price_change_24h_pct)})."
    else:
        response += "Les données marché live sont indisponibles, donc l'analyse se limite aux positions locales."
    st.markdown(f"<div class='card hero'><h3>Réponse Trader AI</h3><p>{response}</p></div>", unsafe_allow_html=True)
