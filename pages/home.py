from __future__ import annotations

import html

import streamlit as st
from components.cards import empty_state
from pages.opportunities import confidence, indicator, percent_score, recommendation, risk, risk_status, score
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


def _opportunity_item(asset: MarketAsset) -> str:
    ai_score = score(asset)
    asset_risk = risk(asset)
    confidence_score = confidence(asset)
    risk_label, risk_class, _ = risk_status(asset_risk)
    return (
        "<div class='mini-item'>"
        "<div class='row'>"
        f"<div><b>{html.escape(asset.name)}</b><p class='muted'>{html.escape(recommendation(ai_score, asset_risk, confidence_score))}</p></div>"
        f"<div style='text-align:right'><b>{percent_score(ai_score)}</b><p class='muted'>Risque : <span class='{risk_class}'>{percent_score(asset_risk)} · {html.escape(risk_label)}</span></p></div>"
        "</div>"
        f"{indicator('Potentiel IA', ai_score)}"
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
    market_cards = "".join(_market_item(asset) for asset in markets[:3]) or "<p class='muted'>Données marché indisponibles.</p>"
    trending_cards = "".join(f"<span class='pill soft'>{html.escape(asset.symbol)}</span> " for asset in trending[:7]) or "<span class='muted'>Indisponible</span>"
    opportunity_cards = "".join(_opportunity_item(asset) for asset in ranked_opportunities) or "<p class='muted'>Aucune opportunité à afficher pour le moment.</p>"
    best_label = f"{best_asset.name} · {percent(best_asset.price_change_24h_pct)}" if best_asset else "Indisponible"
    market_class = "positive" if avg_24h >= 0 else "negative"
    worst_label = f"{worst_asset.name} · {percent(worst_asset.price_change_24h_pct)}" if worst_asset else "Indisponible"

    st.markdown(
        f"""
        <div class='card hero home-hero compact-card'>
            <span class='pill'>{APP_SUBTITLE}</span>
            <h1>{HOME_TITLE}</h1>
            <p class='muted'>{HOME_SUBTITLE}</p>
            <div class='metric'>
                <div><span class='muted'>Portefeuille Binance</span><b>{portfolio_label}</b><p class='muted'>{portfolio_message}</p></div>
                <div><span class='muted'>Mode</span><b>Lecture seule</b></div>
                <div><span class='muted'>Actifs marché</span><b>{len(markets)}</b></div>
            </div>
        </div>
        <div class='dashboard-grid'>
            <section class='card dashboard-span-3 compact-card'>
                <div class='dashboard-section-title'><div><span class='pill'>Vue rapide</span><h3>Essentiel du jour</h3></div></div>
                <div class='metric desktop-kpi-row'>
                    <div><span class='muted'>Valeur portefeuille</span><b>{portfolio_label}</b></div>
                    <div><span class='muted'>Daily P&L</span><b class='{daily_pnl_class}'>{money(daily_pnl, 'USDT')}</b></div>
                    <div><span class='muted'>Opportunités actives</span><b>{len(ranked_opportunities)}</b></div>
                    <div><span class='muted'>Statut marché</span><b class='{market_class}'>{percent(avg_24h)}</b></div>
                </div>
            </section>
            <section class='card dashboard-span-2'>
                <div class='dashboard-section-title'><div><span class='pill'>Portefeuille</span><h2>Résumé premium</h2></div><b>{portfolio_label}</b></div>
                <div class='metric'>
                    <div><span class='muted'>Statut</span><b>{'Connecté' if has_binance_positions else 'À connecter'}</b></div>
                    <div><span class='muted'>Sécurité</span><b>Lecture seule</b></div>
                    <div><span class='muted'>Suivi</span><b>Spot Binance</b></div>
                </div>
            </section>
            <section class='card compact-card'>
                <div class='dashboard-section-title'><div><span class='pill soft'>Insight IA</span><h3>Signal principal</h3></div></div>
                <p class='muted'>Analyse en français, éducative uniquement, basée sur le portefeuille et les marchés chargés.</p>
                <div class='mini-item'><b>Signal à surveiller</b><p class='muted'>{html.escape(best_label)}</p></div>
            </section>
            <section class='card dashboard-span-3'>
                <div class='dashboard-section-title'><div><span class='pill'>Marchés</span><h3>Cartes live</h3></div><b class='{market_class}'>{percent(avg_24h)}</b></div>
                <div class='mini-list desktop-grid-3'>{market_cards}</div>
            </section>
            <section class='card dashboard-span-3'>
                <div class='dashboard-section-title'><div><span class='pill'>Vue marché</span><h3>Marché crypto global</h3></div></div>
                <div class='metric'>
                    <div><span class='muted'>Dominance BTC</span><b>{metrics.get('btc_dominance',0):.1f}%</b></div>
                    <div><span class='muted'>Indice Fear & Greed</span><b>{fear.value if fear.value is not None else '—'} % · {html.escape(fear.label)}</b></div>
                    <div><span class='muted'>Capitalisation crypto totale</span><b>{money(metrics.get('total_market_cap'))}</b></div>
                    <div><span class='muted'>Volume marché 24h</span><b>{money(metrics.get('total_volume'))}</b></div>
                    <div><span class='muted'>Meilleure progression</span><b>{html.escape(best_label)}</b></div>
                    <div><span class='muted'>Plus fort repli</span><b>{html.escape(worst_label)}</b></div>
                    <div><span class='muted'>Actifs tendance</span><b>{trending_cards}</b></div>
                </div>
            </section>
            <section class='card dashboard-span-2'>
                <div class='dashboard-section-title'><div><span class='pill'>Opportunités</span><h3>Top éducatif</h3></div><span class='muted'>Potentiel IA · risque · confiance</span></div>
                <div class='mini-list desktop-grid-3'>{opportunity_cards}</div>
            </section>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not markets:
        empty_state("Données marché indisponibles", "Aucune donnée live n'a pu être chargée. Les pages restent accessibles avec des états vides élégants.")
