from __future__ import annotations

import streamlit as st
from components.cards import asset_card, empty_state
from services.coingecko_service import CoinGeckoService
from services.binance_service import BinanceService
from utils.helpers import money


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]
    bz = services["binance"]
    assert isinstance(cg, CoinGeckoService) and isinstance(bz, BinanceService)
    markets = cg.get_markets()
    binance_summary = bz.spot_portfolio(cg) if bz.configured else None
    portfolio_label = money(binance_summary.total_value_usdt, "USDT") if binance_summary and binance_summary.connected and binance_summary.positions else "Indisponible"
    portfolio_message = "Total réel Binance Spot" if binance_summary and binance_summary.connected and binance_summary.positions else "Aucun solde Binance détecté : connectez Binance en lecture seule ou vérifiez que votre portefeuille Spot contient des actifs."
    st.markdown(f"<div class='card hero'><span class='pill'>Premium crypto cockpit</span><h1>Trader AI</h1><p class='muted'>Dashboard mobile-first, lecture seule, robuste même lorsque les API externes sont indisponibles.</p><div class='metric'><div><span class='muted'>Portefeuille Binance</span><b>{portfolio_label}</b><p class='muted'>{portfolio_message}</p></div><div><span class='muted'>Mode</span><b>Lecture seule</b></div><div><span class='muted'>Actifs marché</span><b>{len(markets)}</b></div></div></div>", unsafe_allow_html=True)
    if markets:
        st.subheader("Marchés suivis")
        for asset in markets[:3]:
            asset_card(asset)
    else:
        empty_state("Données marché indisponibles", "Aucune donnée live n'a pu être chargée. Les pages restent accessibles avec des états vides élégants.")
