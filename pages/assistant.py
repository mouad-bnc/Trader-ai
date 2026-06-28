from __future__ import annotations

import html

import streamlit as st

from services.binance_service import BinanceService
from services.coingecko_service import CoinGeckoService
from services.portfolio_service import PortfolioService
from utils.constants import AI_PAGE_TITLE
from utils.helpers import money, percent


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]
    pf = services["portfolio"]
    bz = services.get("binance")
    assert isinstance(cg, CoinGeckoService) and isinstance(pf, PortfolioService)
    st.markdown(f"<div class='dashboard-micro-title'><div><span class='pill'>Assistant AI</span><h1>{AI_PAGE_TITLE}</h1></div><span class='muted'>Question en haut · réponse compacte</span></div>", unsafe_allow_html=True)
    markets = cg.get_markets()
    binance_summary = bz.spot_portfolio() if isinstance(bz, BinanceService) and bz.configured else None
    summary = pf.summarize(pf.demo_holdings(), markets)
    portfolio_value = binance_summary.total_value_usdt if binance_summary and binance_summary.connected and binance_summary.positions else summary.total_value
    positions_count = len(binance_summary.positions) if binance_summary and binance_summary.connected else len(summary.positions)

    st.markdown(
        "<div class='cockpit-card-sm'><div class='page-kicker'><div><span class='pill'>Assistant contextuel</span>"
        "<p class='muted'>Réponses en français, éducatives uniquement, basées sur le portefeuille disponible et les données marché chargées.</p></div>"
        "<div class='assistant-chip-row'><span class='assistant-chip'>Analyse portefeuille</span><span class='assistant-chip'>Risque BTC</span>"
        "<span class='assistant-chip'>Opportunités</span><span class='assistant-chip'>Résumé marché</span></div></div></div>",
        unsafe_allow_html=True,
    )
    prompt = st.text_input("Votre question", placeholder="Analyse mon portefeuille et le risque actuel")
    if not prompt:
        st.markdown("<div class='cockpit-card-sm'><b>Prêt pour une question</b><p class='muted'>Choisissez une intention ci-dessus ou tapez une question. Analyse temporairement indisponible si les données marché ne chargent pas.</p></div>", unsafe_allow_html=True)
        return

    prompt_l = prompt.lower()
    lines = [f"Ton portefeuille suivi vaut environ {money(portfolio_value)} sur {positions_count} position(s)."]
    if markets:
        best = max(markets, key=lambda a: a.price_change_24h_pct)
        weakest = min(markets, key=lambda a: a.price_change_24h_pct)
        avg_24h = sum(a.price_change_24h_pct for a in markets) / len(markets)
        lines.append(f"La watchlist montre une moyenne 24h de {percent(avg_24h)}. Meilleur momentum: {best.name} ({percent(best.price_change_24h_pct)}). Plus faible: {weakest.name} ({percent(weakest.price_change_24h_pct)}).")
        if "risque" in prompt_l or "risk" in prompt_l:
            lines.append("Réduis le risque avec une taille de position maîtrisée, une diversification raisonnable et un plan écrit avant toute décision.")
        elif "opportun" in prompt_l:
            lines.append(f"À surveiller en priorité: {best.name}, mais attends une confirmation de tendance et un ratio rendement/risque cohérent.")
        else:
            lines.append("Le contexte favorise une lecture graduelle: tendance, volume, volatilité, puis allocation. Aucune action automatique n'est recommandée.")
    else:
        lines.append("Les données marché live sont indisponibles; l'analyse reste limitée au portefeuille local et doit être réévaluée quand les API reviennent.")
    lines.append("Ceci est une information éducative, pas un conseil financier.")
    response = " ".join(lines)
    st.markdown(f"<div class='cockpit-card'><h3>Réponse MSH AI-Invest</h3><p>{html.escape(response)}</p></div>", unsafe_allow_html=True)
