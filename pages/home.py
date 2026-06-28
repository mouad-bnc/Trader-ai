from __future__ import annotations

import html

import streamlit as st
from components.cards import empty_state
from components.charts import sparkline
from pages.opportunities import confidence, percent_score, risk, score
from services.binance_service import BinanceService
from services.coingecko_service import CoinGeckoService, MarketAsset
from utils.constants import APP_SUBTITLE, HOME_SUBTITLE, HOME_TITLE
from utils.helpers import money, percent


def _market_item(asset: MarketAsset) -> str:
    trend_class = "positive" if asset.price_change_24h_pct >= 0 else "negative"
    return (
        "<div class='mini-item'>"
        "<div class='row'>"
        f"<div><b>{html.escape(asset.name)}</b><p class='muted'>{html.escape(asset.symbol)} · Rang #{asset.market_cap_rank or '—'}</p></div>"
        f"<div style='text-align:right'><b>{money(asset.current_price)}</b><p class='{trend_class}'>{percent(asset.price_change_24h_pct)}</p></div>"
        "</div></div>"
    )


def _decision_status(ai_score: float, asset_risk: float, confidence_score: float) -> tuple[str, str]:
    if asset_risk >= 70:
        return "Éviter", "status-critique"
    if ai_score >= 70 and asset_risk < 50 and confidence_score >= 60:
        return "Acheter", "status-excellent"
    if confidence_score < 55 or asset_risk >= 50:
        return "Surveiller", "status-a-surveiller"
    return "Attendre", "status-moyen"


def _short_reason(asset: MarketAsset, ai_score: float, asset_risk: float, confidence_score: float) -> str:
    if asset_risk >= 70:
        return "Volatilité trop élevée pour une décision propre."
    if ai_score >= 70 and confidence_score >= 60:
        return "Momentum et confiance alignés, risque contenu."
    if confidence_score < 55:
        return "Signal incomplet, attendre plus de confirmation."
    return "Potentiel présent mais timing encore à valider."


def _opportunity_item(asset: MarketAsset) -> str:
    ai_score = score(asset)
    asset_risk = risk(asset)
    confidence_score = confidence(asset)
    status, status_class = _decision_status(ai_score, asset_risk, confidence_score)
    return (
        "<div class='mini-item decision-card'>"
        "<div class='decision-head'>"
        f"<div><b>{html.escape(asset.symbol)}</b><p class='muted'>{html.escape(asset.name)} · {money(asset.current_price)}</p></div>"
        f"<span class='pill soft {status_class}'>{html.escape(status)}</span>"
        "</div>"
        "<div class='decision-metrics'>"
        f"<span>Potentiel IA <b>{percent_score(ai_score)}</b></span>"
        f"<span>Risque <b>{percent_score(asset_risk)}</b></span>"
        f"<span>Confiance <b>{percent_score(confidence_score)}</b></span>"
        "</div>"
        f"<p class='muted decision-reason'>{html.escape(_short_reason(asset, ai_score, asset_risk, confidence_score))}</p>"
        "</div>"
    )


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]
    bz = services["binance"]
    assert isinstance(cg, CoinGeckoService) and isinstance(bz, BinanceService)
    markets = cg.get_markets()
    metrics = cg.global_metrics()
    fear = cg.fear_greed()
    trending = cg.trending()
    binance_summary = bz.spot_portfolio(cg) if bz.configured else None
    has_binance_positions = bool(binance_summary and binance_summary.connected and binance_summary.positions)
    portfolio_label = money(binance_summary.total_value_usdt, "USDT") if has_binance_positions else "Indisponible"
    daily_pnl = binance_summary.pnl_24h_usdt if has_binance_positions and binance_summary and binance_summary.pnl_24h_usdt else 0
    daily_pnl_class = "positive" if daily_pnl >= 0 else "negative"
    portfolio_message = "Total réel Binance Spot" if has_binance_positions else "Connectez Binance en lecture seule ou vérifiez que votre portefeuille Spot contient des actifs."
    avg_24h = sum(asset.price_change_24h_pct for asset in markets) / len(markets) if markets else 0
    best_asset = max(markets, key=lambda asset: asset.price_change_24h_pct) if markets else None
    worst_asset = min(markets, key=lambda asset: asset.price_change_24h_pct) if markets else None
    ranked_opportunities = sorted(markets, key=score, reverse=True)[:3]
    avg_risk = sum(risk(asset) for asset in markets) / len(markets) if markets else 0
    avg_confidence = sum(confidence(asset) for asset in markets) / len(markets) if markets else 0
    top_opportunity = ranked_opportunities[0] if ranked_opportunities else None
    market_cards = "".join(_market_item(asset) for asset in markets[:6]) or "<p class='muted'>Données marché indisponibles.</p>"
    trending_cards = "".join(f"<span class='pill soft'>{html.escape(asset.symbol)}</span> " for asset in trending[:7]) or "<span class='muted'>Indisponible</span>"
    opportunity_cards = "".join(_opportunity_item(asset) for asset in ranked_opportunities) or "<p class='muted'>Aucune opportunité à afficher pour le moment.</p>"
    best_label = f"{best_asset.name} · {percent(best_asset.price_change_24h_pct)}" if best_asset else "Indisponible"
    market_class = "positive" if avg_24h >= 0 else "negative"
    worst_label = f"{worst_asset.name} · {percent(worst_asset.price_change_24h_pct)}" if worst_asset else "Indisponible"
    chart_asset = best_asset or (markets[0] if markets else None)
    chart_values = chart_asset.sparkline if chart_asset else []
    chart_title = f"{chart_asset.name} · performance 7j" if chart_asset else "Performance portefeuille"
    chart_positive = (chart_values[-1] >= chart_values[0]) if len(chart_values) >= 2 else avg_24h >= 0
    chart_svg = sparkline(chart_values, chart_positive)
    top_opportunity_card = _opportunity_item(top_opportunity) if top_opportunity else "<p class='muted'>Aucune opportunité détectée.</p>"

    st.markdown(
        f"""
        <div class='focus-shell'>
            <section class='card cockpit-header compact-card'>
                <div>
                    <span class='pill'>{APP_SUBTITLE}</span>
                    <h1>{HOME_TITLE}</h1>
                    <p class='muted'>{HOME_SUBTITLE}</p>
                </div>
                <div class='cockpit-meta'>
                    <b>MSH AI-Invest</b>
                    <span>Dashboard focus · lecture seule</span>
                </div>
            </section>
            <section class='kpi-strip'>
                <div class='kpi-tile'><span>Valeur portefeuille</span><b>{portfolio_label}</b><small>{portfolio_message}</small></div>
                <div class='kpi-tile'><span>P&L 24h</span><b class='{daily_pnl_class}'>{money(daily_pnl, 'USDT')}</b><small>Binance Spot</small></div>
                <div class='kpi-tile'><span>Risque</span><b>{avg_risk:.0f} %</b><small>Score agrégé</small></div>
                <div class='kpi-tile'><span>Confiance</span><b>{avg_confidence:.0f} %</b><small>Qualité données</small></div>
                <div class='kpi-tile'><span>Statut marché</span><b class='{market_class}'>{percent(avg_24h)}</b><small>Moyenne actifs suivis</small></div>
                <div class='kpi-tile'><span>Top opportunité</span><b>{html.escape(top_opportunity.symbol if top_opportunity else '—')}</b><small>{len(ranked_opportunities)} décisions IA</small></div>
                <div class='kpi-tile'><span>Fear & Greed</span><b>{fear.value if fear.value is not None else '—'} %</b><small>{html.escape(fear.label)}</small></div>
                <div class='kpi-tile'><span>Dominance BTC</span><b>{metrics.get('btc_dominance',0):.1f}%</b><small>Marché global</small></div>
            </section>
            <section class='focus-grid'>
                <article class='card main-chart-panel'>
                    <div class='dashboard-section-title'><div><span class='pill'>Graphique principal</span><h3>{html.escape(chart_title)}</h3></div><b class='{market_class}'>{percent(avg_24h)}</b></div>
                    <div class='main-chart'>{chart_svg}</div>
                </article>
                <aside class='right-stack'>
                    <div class='card compact-card stack-card'>
                        <span class='pill soft'>Résumé IA quotidien</span>
                        <p class='muted'>Marché {percent(avg_24h)}. Meilleur signal : <b>{html.escape(best_label)}</b>. Pire repli : <b>{html.escape(worst_label)}</b>.</p>
                    </div>
                    <div class='card compact-card stack-card top-opportunity-card'>
                        <span class='pill'>Top opportunité</span>
                        {top_opportunity_card}
                    </div>
                    <div class='card compact-card stack-card'>
                        <span class='pill soft'>Risque</span>
                        <div class='mini-item'><b>{'Connecté' if has_binance_positions else 'À connecter'}</b><p class='muted'>Sécurité lecture seule · suivi Spot Binance · aucune exécution.</p></div>
                    </div>
                </aside>
            </section>
            <section class='below-grid'>
                <article class='card market-panel'>
                    <div class='dashboard-section-title'><div><span class='pill'>Marchés</span><h3>Cartes compactes</h3></div><b class='{market_class}'>{percent(avg_24h)}</b></div>
                    <div class='mini-list desktop-grid-3'>{market_cards}</div>
                </article>
                <article class='card compact-card movers-panel'>
                    <div class='dashboard-section-title'><div><span class='pill soft'>Gainers / Losers</span><h3>24h</h3></div></div>
                    <div class='mini-item'><b>Top gainer</b><p class='muted positive'>{html.escape(best_label)}</p></div>
                    <div class='mini-item'><b>Top loser</b><p class='muted negative'>{html.escape(worst_label)}</p></div>
                </article>
                <article class='card compact-card watchlist-panel'>
                    <div class='dashboard-section-title'><div><span class='pill soft'>Watchlist</span><h3>Tendances</h3></div></div>
                    <p>{trending_cards}</p>
                    <div class='mini-item'><b>Volume 24h</b><p class='muted'>{money(metrics.get('total_volume'))}</p></div>
                </article>
                <article class='card opportunities-panel'>
                    <div class='dashboard-section-title'><div><span class='pill'>Opportunités</span><h3>Décisions rapides</h3></div><span class='muted'>Asset · prix · potentiel · risque · confiance</span></div>
                    <div class='mini-list desktop-grid-3'>{opportunity_cards}</div>
                </article>
            </section>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not markets:
        empty_state("Données marché indisponibles", "Aucune donnée live n'a pu être chargée. Les pages restent accessibles avec des états vides élégants.")
