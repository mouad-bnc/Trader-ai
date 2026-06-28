from __future__ import annotations
import streamlit as st
from components.cards import asset_card, empty_state
from services.coingecko_service import CoinGeckoService, MarketAsset


def score(asset: MarketAsset) -> float:
    return 50 + asset.price_change_7d_pct * 1.8 + asset.price_change_24h_pct - max(0, (asset.high_24h - asset.low_24h) / asset.current_price * 30 if asset.current_price else 0)


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]
    assert isinstance(cg, CoinGeckoService)
    st.title("Opportunités")
    markets = sorted(cg.get_markets(), key=score, reverse=True)
    if not markets:
        empty_state("Aucune opportunité", "L'analyse reprendra automatiquement lorsque les prix seront disponibles.")
    for asset in markets[:5]:
        asset_card(asset)
