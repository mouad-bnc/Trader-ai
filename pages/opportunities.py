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
    if asset_risk >= 70:
        return "Risque élevé"
    if confidence_score < 55:
        return "À surveiller"
    if ai_score >= 70 and asset_risk < 50:
        return "Opportunité IA"
    return "Attendre confirmation"


def _compact_metric(label: str, value: float, *, risk_indicator: bool = False, display: str | None = None) -> str:
    status, status_class, _ = risk_status(value) if risk_indicator else positive_status(value)
    shown = display or percent_score(value)
    return (
        "<div class='metric-chip'>"
        f"<span>{html.escape(label)}</span><b class='{status_class}'>{html.escape(shown)}</b>"
        f"<small>{html.escape(status)}</small>"
        "</div>"
    )


def _why_points(asset: MarketAsset, asset_risk: float) -> list[str]:
    mom = momentum(asset)
    avg_price = (asset.high_24h + asset.low_24h) / 2 if asset.high_24h and asset.low_24h else asset.current_price
    volume_label = "Volume élevé" if asset.total_volume and asset.market_cap and asset.total_volume >= asset.market_cap * 0.03 else "Volume à confirmer"
    trend = "Tendance confirmée" if mom > 1 and asset.current_price >= avg_price else "Tendance non confirmée"
    risk_label, _, _ = risk_status(asset_risk)
    return [
        f"Momentum {'positif' if mom >= 0 else 'négatif'} sur les données 24h/7j.",
        f"{volume_label} par rapport aux données disponibles.",
        f"{trend} par le positionnement du prix.",
        f"Risque {risk_label.lower()} selon volatilité et momentum.",
    ]


def _target_section(asset: MarketAsset, ai_score: float) -> str:
    if asset.current_price <= 0 or asset.high_24h <= 0 or asset.low_24h <= 0:
        return "<div class='target-grid'><p class='muted'>Objectif indisponible pour le moment.</p></div>"
    entry = asset.low_24h + (asset.high_24h - asset.low_24h) * 0.35
    objective = max(asset.high_24h, asset.current_price * (1 + ai_score / 1000))
    potential = ((objective - asset.current_price) / asset.current_price) * 100 if asset.current_price else 0
    horizon = "Court terme" if abs(momentum(asset)) >= 3 else "À confirmer"
    return (
        "<div class='target-grid'>"
        f"<div><span class='muted'>Prix actuel</span><b>{money(asset.current_price)}</b></div>"
        f"<div><span class='muted'>Entrée idéale</span><b>{money(entry)}</b></div>"
        f"<div><span class='muted'>Objectif IA</span><b>{money(objective)}</b></div>"
        f"<div><span class='muted'>Potentiel estimé</span><b>{percent(potential)}</b></div>"
        f"<div><span class='muted'>Horizon</span><b>{html.escape(horizon)}</b></div>"
        "</div>"
    )



def _decision_table(markets: list[MarketAsset], limit: int = 12) -> str:
    rows = []
    for asset in markets[:limit]:
        ai_score = score(asset)
        asset_risk = risk(asset)
        confidence_score = confidence(asset)
        asset_momentum = momentum(asset)
        bias = recommendation(ai_score, asset_risk, confidence_score)
        reason = _why_points(asset, asset_risk)[0]
        target = "—"
        if asset.current_price > 0 and asset.high_24h > 0:
            target = money(max(asset.high_24h, asset.current_price * (1 + ai_score / 1000)))
        rows.append(
            "<tr>"
            f"<td data-label='Asset'><b>{html.escape(asset.symbol)}</b><br><span class='muted'>{html.escape(asset.name)}</span></td>"
            f"<td data-label='Prix'>{money(asset.current_price)}</td>"
            f"<td data-label='Potentiel IA'><b>{percent_score(ai_score)}</b></td>"
            f"<td data-label='Risque'><b>{percent_score(asset_risk)}</b></td>"
            f"<td data-label='Confiance'><b>{percent_score(confidence_score)}</b></td>"
            f"<td data-label='Momentum'><b>{percent(asset_momentum)}</b></td>"
            f"<td data-label='Status'><span class='pill soft'>{html.escape(bias)}</span></td>"
            f"<td data-label='Raison'><span class='muted'>{html.escape(reason)}</span></td>"
            f"<td data-label='Cible'>{html.escape(target)}</td>"
            "</tr>"
        )
    return (
        "<div class='cockpit-table-wrap'><table class='cockpit-table'>"
        "<thead><tr><th>Asset</th><th>Prix</th><th>Potentiel IA</th><th>Risque</th><th>Confiance</th><th>Momentum</th><th>Status</th><th>Raison courte</th><th>Cible</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )

def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]
    assert isinstance(cg, CoinGeckoService)
    st.title("Opportunités")
    markets = cg.get_markets()
    ranked = sorted(markets, key=score, reverse=True)
    if not ranked:
        empty_state("Aucune opportunité", "L'analyse reprendra automatiquement lorsque les prix seront disponibles.")
        return

    st.markdown("<div class='cockpit-container'><div class='cockpit-card-sm'><span class='pill'>Scanner IA</span><p class='muted'>Vue décision compacte : asset, prix, potentiel, risque, confiance, momentum, status, raison et cible. Ceci n'est pas un conseil financier.</p></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='cockpit-card'>{_decision_table(ranked)}</div>", unsafe_allow_html=True)
    _render_scanner(ranked)
    st.markdown("</div>", unsafe_allow_html=True)
    for asset in ranked[:3]:
        ai_score = score(asset)
        asset_risk = risk(asset)
        asset_vol = volatility(asset)
        confidence_score = confidence(asset)
        asset_momentum = momentum(asset)
        bias = recommendation(ai_score, asset_risk, confidence_score)
        why = "".join(f"<li>{html.escape(point)}</li>" for point in _why_points(asset, asset_risk)[:4])
        st.markdown(
            f"<article class='card opportunity-card compact-card'><div class='opportunity-head'>"
            f"<div><span class='pill soft'>{html.escape(bias)}</span><h3>{html.escape(asset.name)}</h3>"
            f"<p class='muted'>{html.escape(asset.symbol)} · {money(asset.current_price)}</p></div>"
            f"<div class='opportunity-price'><b>{percent_score(ai_score)}</b><span>Potentiel IA</span></div></div>"
            f"<div class='metric-chips compact-metrics-row'>"
            f"{_compact_metric('Potentiel IA', ai_score)}"
            f"{_compact_metric('Risque', asset_risk, risk_indicator=True)}"
            f"{_compact_metric('Confiance', confidence_score)}"
            f"{_compact_metric('Momentum', clamp(asset_momentum, 0, 100), display=percent(asset_momentum))}"
            f"{_compact_metric('Volatilité', clamp(asset_vol, 0, 100), risk_indicator=True)}"
            f"</div>"
            f"<div class='thin-bars'>{indicator('Potentiel IA', ai_score)}{indicator('Confiance', confidence_score)}{indicator('Risque', asset_risk, risk_indicator=True)}</div>"
            f"<div class='opportunity-details'><div><h4>Pourquoi ?</h4><ul>{why}</ul></div>"
            f"<div><h4>Cibles</h4>{_target_section(asset, ai_score)}</div></div></article>",
            unsafe_allow_html=True,
        )

def _scanner_explanation(kind: str, asset: MarketAsset) -> str:
    if kind == "Breakouts à surveiller":
        return "Prix proche du haut 24h avec momentum positif."
    if kind == "Actifs survendus":
        return "Repli marqué pouvant créer une zone de surveillance."
    if kind == "Momentum fort":
        return "Tendance 24h/7j favorable avec confirmation relative."
    return "Volume élevé par rapport aux actifs suivis, mouvement à vérifier."


def _render_scanner(markets: list[MarketAsset]) -> None:
    avg_volume = sum(a.total_volume for a in markets) / len(markets) if markets else 0
    groups = {
        "Breakouts à surveiller": [a for a in markets if a.high_24h and a.current_price >= a.high_24h * 0.985 and momentum(a) > 0],
        "Actifs survendus": [a for a in markets if a.price_change_24h_pct <= -3 or momentum(a) <= -4],
        "Momentum fort": [a for a in markets if momentum(a) >= 3],
        "Volumes inhabituels": [a for a in markets if avg_volume and a.total_volume >= avg_volume * 1.35],
    }
    for title, assets in groups.items():
        cards = []
        for asset in assets[:3]:
            conf = confidence(asset)
            asset_risk = risk(asset)
            cards.append(
                f"<div class='mini-item'><div class='row'><div><b>{html.escape(asset.name)}</b>"
                f"<p class='muted'>{html.escape(_scanner_explanation(title, asset))}</p></div>"
                f"<div style='text-align:right'><b>Confiance {percent_score(conf)}</b>"
                f"<p class='muted'>Risque {percent_score(asset_risk)}</p></div></div></div>"
            )
        body = "".join(cards) or "<p class='muted'>Aucun actif détecté pour ce filtre.</p>"
        st.markdown(f"<div class='cockpit-card-sm'><div class='dashboard-micro-title'><h3>{html.escape(title)}</h3></div><div class='mini-list'>{body}</div></div>", unsafe_allow_html=True)
