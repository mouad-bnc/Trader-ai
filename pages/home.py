from __future__ import annotations

import streamlit as st
from components.cards import asset_card, empty_state
from services.coingecko_service import CoinGeckoService
from services.portfolio_service import PortfolioService
from utils.helpers import money, percent


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]
    pf = services["portfolio"]
    assert isinstance(cg, CoinGeckoService) and isinstance(pf, PortfolioService)
    markets = cg.get_markets()
    summary = pf.summarize(pf.demo_holdings(), markets)
    st.markdown(f"<div class='card hero'><span class='pill'>Premium crypto cockpit</span><h1>Trader AI</h1><p class='muted'>Dashboard mobile-first, lecture seule, robuste même lorsque les API externes sont indisponibles.</p><div class='metric'><div><span class='muted'>Portefeuille</span><b>{money(summary.total_value)}</b></div><div><span class='muted'>PnL</span><b class='{ 'positive' if summary.pnl >= 0 else 'negative' }'>{percent(summary.pnl_pct)}</b></div><div><span class='muted'>Actifs</span><b>{len(markets)}</b></div></div></div>", unsafe_allow_html=True)
    if markets:
        st.subheader("Marchés suivis")
        for asset in markets[:3]:
            asset_card(asset)
    else:
        empty_state("Données marché indisponibles", "Aucune donnée live n'a pu être chargée. Les pages restent accessibles avec des états vides élégants.")
