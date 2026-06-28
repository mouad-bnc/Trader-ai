from __future__ import annotations

import html

import streamlit as st

from components.cards import empty_state
from services.coingecko_service import CoinGeckoService, MarketAsset
from utils.helpers import clamp, money, percent


def volatility(asset: MarketAsset) -> float:
    if not asset.current_price:
        return 0.0
    return abs(asset.high_24h - asset.low_24h) / asset.current_price * 100


def momentum(asset: MarketAsset) -> float:
    return asset.price_change_24h_pct * 0.45 + asset.price_change_7d_pct * 0.55


def risk(asset: MarketAsset) -> float:
    rank_penalty = min(asset.market_cap_rank or 100, 100) / 100 * 20
    return clamp(volatility(asset) * 2.2 + max(0, -momentum(asset)) * 1.5 + rank_penalty, 0, 100)


def score(asset: MarketAsset) -> float:
    return clamp(55 + momentum(asset) * 2.1 - risk(asset) * 0.35, 0, 100)


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]
    assert isinstance(cg, CoinGeckoService)
    st.title("Opportunités")
    markets = cg.get_markets()
    ranked = sorted(markets, key=score, reverse=True)
    if not ranked:
        empty_state("Aucune opportunité", "L'analyse reprendra automatiquement lorsque les prix seront disponibles.")
        return

    st.markdown("<div class='card'><span class='pill'>Analyse éducative</span><p class='muted'>Classement basé sur score IA, momentum, risque et volatilité. Ceci n'est pas un conseil financier.</p></div>", unsafe_allow_html=True)
    for asset in ranked[: max(3, min(5, len(ranked)))]:
        ai_score = score(asset)
        asset_risk = risk(asset)
        asset_vol = volatility(asset)
        bias = "Accumulation prudente" if ai_score >= 65 and asset_risk < 55 else "Surveillance" if ai_score >= 50 else "Attendre confirmation"
        st.markdown(
            f"<div class='card'><div class='row'><div><h3>{html.escape(asset.name)}</h3>"
            f"<p class='muted'>{html.escape(asset.symbol)} · {html.escape(bias)}</p></div>"
            f"<div style='text-align:right'><b>{ai_score:.0f}/100</b><p class='muted'>{money(asset.current_price)}</p></div></div>"
            f"<div class='metric'><div><span class='muted'>Momentum</span><b class='{ 'positive' if momentum(asset) >= 0 else 'negative' }'>{percent(momentum(asset))}</b></div>"
            f"<div><span class='muted'>Risque</span><b>{asset_risk:.0f}/100</b></div>"
            f"<div><span class='muted'>Volatilité</span><b>{asset_vol:.1f}%</b></div></div></div>",
            unsafe_allow_html=True,
        )
