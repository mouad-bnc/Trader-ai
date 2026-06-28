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


def confidence(asset: MarketAsset) -> float:
    data_points = 0
    data_points += 1 if asset.current_price > 0 else 0
    data_points += 1 if asset.total_volume > 0 else 0
    data_points += 1 if asset.market_cap_rank > 0 else 0
    data_points += 1 if asset.high_24h > 0 and asset.low_24h > 0 else 0
    return clamp(45 + data_points * 12 - risk(asset) * 0.15, 0, 100)


def percent_score(value: float) -> str:
    return f"{value:.0f} %"


def positive_status(value: float) -> tuple[str, str, str]:
    if value >= 85:
        return "Excellent", "status-excellent", "progress-green"
    if value >= 70:
        return "Bon", "status-bon", "progress-green"
    if value >= 50:
        return "Moyen", "status-moyen", "progress-yellow"
    if value >= 30:
        return "À surveiller", "status-a-surveiller", "progress-orange"
    return "Critique", "status-critique", "progress-red"


def risk_status(value: float) -> tuple[str, str, str]:
    if value <= 29:
        return "Faible", "status-faible", "progress-green"
    if value <= 49:
        return "Modéré", "status-modere", "progress-yellow"
    if value <= 69:
        return "Élevé", "status-eleve", "progress-orange"
    return "Très élevé", "status-tres-eleve", "progress-red"


def indicator(label: str, value: float, *, risk_indicator: bool = False) -> str:
    status, status_class, progress_class = risk_status(value) if risk_indicator else positive_status(value)
    safe_label = html.escape(label)
    safe_status = html.escape(status)
    width = clamp(value, 0, 100)
    return (
        "<div>"
        f"<div class='score-line'><span class='score-label'>{safe_label}</span><b class='score-value {status_class}'>{percent_score(value)}</b></div>"
        f"<div class='progress {progress_class}' aria-label='{safe_label} {percent_score(value)}'><span style='width:{width:.0f}%'></span></div>"
        f"<p class='muted {status_class}'>{safe_status}</p>"
        "</div>"
    )


def recommendation(ai_score: float, asset_risk: float, confidence_score: float) -> str:
    if confidence_score < 55:
        return "Surveiller : données encore limitées"
    if ai_score >= 70 and asset_risk < 50:
        return "Accumulation prudente"
    if ai_score >= 55 and asset_risk < 70:
        return "Observer et attendre un bon point d’entrée"
    return "Attendre confirmation"


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]
    assert isinstance(cg, CoinGeckoService)
    st.title("Opportunités")
    markets = cg.get_markets()
    ranked = sorted(markets, key=score, reverse=True)
    if not ranked:
        empty_state("Aucune opportunité", "L'analyse reprendra automatiquement lorsque les prix seront disponibles.")
        return

    st.markdown("<div class='card'><span class='pill'>Analyse éducative</span><p class='muted'>Top 3 généré depuis les données marché CoinGecko : score, risque, confiance et recommandation. Ceci n'est pas un conseil financier.</p></div>", unsafe_allow_html=True)
    for asset in ranked[:3]:
        ai_score = score(asset)
        asset_risk = risk(asset)
        asset_vol = volatility(asset)
        confidence_score = confidence(asset)
        bias = recommendation(ai_score, asset_risk, confidence_score)
        st.markdown(
            f"<div class='card'><div class='row'><div><h3>{html.escape(asset.name)}</h3>"
            f"<p class='muted'>{html.escape(asset.symbol)} · {html.escape(bias)}</p></div>"
            f"<div style='text-align:right'><b>{percent_score(ai_score)}</b><p class='muted'>{money(asset.current_price)}</p></div></div>"
            f"<div class='metric'>{indicator('Score', ai_score)}"
            f"{indicator('Risque', asset_risk, risk_indicator=True)}"
            f"{indicator('Confiance', confidence_score)}"
            f"<div><span class='muted'>Momentum</span><b class='{ 'positive' if momentum(asset) >= 0 else 'negative' }'>{percent(momentum(asset))}</b></div>"
            f"<div><span class='muted'>Volatilité</span><b>{asset_vol:.1f}%</b></div></div></div>",
            unsafe_allow_html=True,
        )
