from __future__ import annotations

import html

import streamlit as st
from components.charts import allocation_bar, allocation_pie
from components.cards import empty_state
from services.binance_service import BinancePortfolioSummary, BinanceService
from services.coingecko_service import CoinGeckoService
from services.portfolio_service import PortfolioService, PortfolioSummary
from utils.helpers import clamp, money, percent


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]; pf = services["portfolio"]; bz = services["binance"]
    assert isinstance(cg, CoinGeckoService) and isinstance(pf, PortfolioService) and isinstance(bz, BinanceService)
    st.title("Portefeuille")

    if bz.configured:
        summary = bz.account_portfolio(cg)
        if summary.connected:
            _render_binance_portfolio(summary)
        else:
            message = html.escape(summary.status_message or "Vérifiez les secrets Streamlit BINANCE_API_KEY et BINANCE_API_SECRET. Aucun secret n'est affiché.")
            st.markdown(f"<div class='card hero'><span class='pill soft'>Connexion Binance indisponible</span><p class='muted'>{message}</p></div>", unsafe_allow_html=True)
            _render_binance_debug_panel(summary.debug)
            _render_manual_portfolio(pf.summarize([]), pf)
    else:
        st.markdown("<div class='card hero'><span class='pill soft'>Binance non configuré</span><p class='muted'>Ajoutez BINANCE_API_KEY et BINANCE_API_SECRET aux secrets Streamlit pour synchroniser tous vos comptes Binance en lecture seule.</p></div>", unsafe_allow_html=True)
        empty_state("Aucun portefeuille Binance", "Aucune donnée fictive n’est affichée : connectez Binance en lecture seule pour synchroniser vos avoirs réels.")
        _render_binance_debug_panel(bz.last_debug)
        _render_manual_portfolio(pf.summarize([]), pf)


def _render_binance_debug_panel(debug: dict[str, object]) -> None:
    """Safe diagnostics for Binance read-only synchronization."""
    base_url = html.escape(str(debug.get("base_url") or "https://api.binance.com"))
    status_code = debug.get("status_code") if debug.get("status_code") is not None else "Indisponible"
    error_message = html.escape(str(debug.get("error") or "Aucune"))
    detected_symbols = debug.get("detected_symbols")
    if not isinstance(detected_symbols, list):
        detected_symbols = []
    symbols_label = ", ".join(html.escape(str(symbol)) for symbol in detected_symbols[:5]) or "Aucun"

    with st.expander("Diagnostic Binance sécurisé", expanded=False):
        st.write(f"URL de base utilisée : {base_url}")
        st.write(f"API Key présente : {'Oui' if debug.get('api_key_present') else 'Non'}")
        st.write(f"API Secret présent : {'Oui' if debug.get('api_secret_present') else 'Non'}")
        st.write(f"Status HTTP Binance : {status_code}")
        st.write(f"Message d'erreur Binance : {error_message}")
        st.write(f"Nombre de balances reçues : {debug.get('balances_returned', 0)}")
        st.write(f"Nombre de balances non nulles : {debug.get('non_zero_balances', 0)}")
        st.write(f"5 premiers symboles détectés : {symbols_label}")
        endpoints = debug.get("endpoints")
        if isinstance(endpoints, dict) and endpoints:
            st.write("Endpoints synchronisés :", endpoints)


def _render_binance_portfolio(summary: BinancePortfolioSummary) -> None:
    pnl_class = "positive" if (summary.pnl_24h_usdt or 0) >= 0 else "negative"
    pnl_label = "P&L 24h estimé indisponible"
    if summary.pnl_24h_usdt is not None and summary.pnl_24h_pct is not None:
        pnl_label = f"P&L 24h estimé {money(summary.pnl_24h_usdt)} · {percent(summary.pnl_24h_pct)}"

    last_sync = summary.last_sync_at.strftime("%d %b %Y · %H:%M UTC") if summary.last_sync_at else "Indisponible"
    st.markdown(
        f"<div class='card hero'><span class='pill'>Binance connecté en lecture seule</span>"
        f"<h2>{money(summary.total_value_usdt, 'USDT')}</h2>"
        f"<p class='{pnl_class}'>{html.escape(pnl_label)}</p>"
        f"<p class='muted'>{html.escape(summary.status_message)}</p>"
        f"<p class='muted'>Dernière synchronisation: {html.escape(last_sync)}</p>"
        f"<p class='muted'>Spot Binance lecture seule · Aucun endpoint de trading, transfert ou retrait.</p></div>",
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(6)
    metric_cols[0].metric("Total portfolio", money(summary.total_value_usdt, "USDT"))
    metric_cols[1].metric("Spot", money(summary.spot_value_usdt, "USDT"))
    metric_cols[2].metric("Futures", money(summary.futures_value_usdt, "USDT"))
    metric_cols[3].metric("Earn", money(summary.earn_value_usdt, "USDT"))
    metric_cols[4].metric("Funding", money(summary.funding_value_usdt, "USDT"))
    metric_cols[5].metric("Assets", str(summary.asset_count))

    if summary.endpoint_warnings:
        warnings = "".join(f"<li>{html.escape(warning)}</li>" for warning in summary.endpoint_warnings)
        st.markdown(f"<div class='card'><span class='pill soft'>Synchronisation partielle</span><p class='muted'>Certains endpoints Binance sont indisponibles, les autres soldes restent affichés.</p><ul>{warnings}</ul></div>", unsafe_allow_html=True)

    if not summary.positions:
        empty_state("Synchronisation Binance vide", "Binance est connecté en lecture seule, mais aucun solde non nul n'a été trouvé sur les endpoints disponibles.")
        _render_binance_debug_panel(summary.debug)
        return

    allocations = {position.asset: position.allocation_pct for position in summary.positions}
    st.subheader("Intelligence portefeuille")
    _render_portfolio_intelligence(summary, allocations)

    st.subheader("Allocation par actif")
    allocation_bar(allocations)
    allocation_pie(allocations)

    st.subheader("Insights IA")
    _render_ai_insights(summary)

    st.subheader("Plus grandes positions")

    for pos in summary.positions[:10]:
        pnl_text = "P&L indisponible"
        pnl_class = "muted"
        if pos.pnl_24h_usdt is not None and pos.pnl_24h_pct is not None:
            pnl_class = "positive" if pos.pnl_24h_usdt >= 0 else "negative"
            pnl_text = f"{money(pos.pnl_24h_usdt)} · {percent(pos.pnl_24h_pct)}"
        price_text = money(pos.price_usdt, "USDT") if pos.price_usdt else "Prix USDT indisponible"
        wallets_text = " · ".join(f"{html.escape(wallet)} {amount:g}" for wallet, amount in sorted(pos.wallet_amounts.items()) if amount > 0)
        st.markdown(
            f"<div class='card'><div class='row'><div>"
            f"<h3>{html.escape(pos.asset)}</h3>"
            f"<p class='muted'>{pos.total:g} {html.escape(pos.asset)} · Libre {pos.free:g} · Bloqué {pos.locked:g}</p>"
            f"<p class='muted'>{wallets_text}</p>"
            f"<p class='muted'>Prix: {html.escape(price_text)} · Allocation {pos.allocation_pct:.1f}%</p>"
            f"</div><div style='text-align:right'><b>{money(pos.estimated_value_usdt, 'USDT')}</b>"
            f"<p class='{pnl_class}'>{html.escape(pnl_text)}</p></div></div></div>",
            unsafe_allow_html=True,
        )


def _render_manual_portfolio(summary: PortfolioSummary, pf: PortfolioService) -> None:
    st.markdown(
        f"<div class='card hero'><span class='pill'>Mode portefeuille manuel</span>"
        f"<h2>{money(summary.total_value)}</h2>"
        f"<p class='{ 'positive' if summary.pnl >= 0 else 'negative' }'>{money(summary.pnl)} · {percent(summary.pnl_pct)}</p>"
        f"<p class='muted'>Ajoutez BINANCE_API_KEY et BINANCE_API_SECRET aux secrets Streamlit pour activer la lecture seule Binance.</p></div>",
        unsafe_allow_html=True,
    )
    if not summary.positions:
        empty_state("Aucune position", "Connectez Binance en lecture seule ou importez vos positions plus tard.")
        return
    for pos in summary.positions:
        st.markdown(
            f"<div class='card'><div class='row'><div><h3>{html.escape(pos.holding.name)}</h3>"
            f"<p class='muted'>{pos.holding.quantity:g} {html.escape(pos.holding.symbol)}</p></div>"
            f"<div style='text-align:right'><b>{money(pos.value)}</b>"
            f"<p class='{ 'positive' if pos.pnl >= 0 else 'negative' }'>{percent(pos.pnl_pct)}</p></div></div></div>",
            unsafe_allow_html=True,
        )
    allocation_bar(pf.allocation(summary))


def _performance_label(value_usdt: float | None, value_pct: float | None) -> str:
    if value_usdt is None or value_pct is None:
        return "Historique insuffisant pour calculer cette performance."
    return f"{money(value_usdt, 'USDT')} · {percent(value_pct)}"


def _render_portfolio_intelligence(summary: BinancePortfolioSummary, allocations: dict[str, float]) -> None:
    daily = _performance_label(summary.pnl_24h_usdt, summary.pnl_24h_pct)
    weekly = "Historique insuffisant pour calculer cette performance."
    monthly = "Historique insuffisant pour calculer cette performance."
    performers = [p for p in summary.positions if p.pnl_24h_pct is not None]
    best = max(performers, key=lambda p: p.pnl_24h_pct or 0, default=None)
    worst = min(performers, key=lambda p: p.pnl_24h_pct or 0, default=None)
    best_label = f"{html.escape(best.asset)} · {percent(best.pnl_24h_pct)}" if best else "Historique insuffisant pour calculer cette performance."
    worst_label = f"{html.escape(worst.asset)} · {percent(worst.pnl_24h_pct)}" if worst else "Historique insuffisant pour calculer cette performance."
    st.markdown(
        f"<div class='card'><div class='metric'>"
        f"<div><span class='muted'>P&L quotidien estimé</span><b>{html.escape(daily)}</b></div>"
        f"<div><span class='muted'>P&L hebdomadaire estimé</span><b>{html.escape(weekly)}</b></div>"
        f"<div><span class='muted'>P&L mensuel estimé</span><b>{html.escape(monthly)}</b></div>"
        f"<div><span class='muted'>Meilleur performer</span><b>{best_label}</b></div>"
        f"<div><span class='muted'>Pire performer</span><b>{worst_label}</b></div>"
        f"<div><span class='muted'>Exposition principale</span><b>{html.escape(max(allocations, key=allocations.get) if allocations else 'Indisponible')}</b></div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )


def _status_positive(value: float) -> str:
    if value >= 85: return "Excellent"
    if value >= 70: return "Bon"
    if value >= 50: return "Moyen"
    if value >= 30: return "À surveiller"
    return "Critique"


def _status_risk(value: float) -> str:
    if value <= 29: return "Faible"
    if value <= 49: return "Modéré"
    if value <= 69: return "Élevé"
    return "Très élevé"


def _render_ai_insights(summary: BinancePortfolioSummary) -> None:
    allocations = [p.allocation_pct for p in summary.positions]
    largest = max(allocations or [0])
    diversification = clamp(100 - max(0, largest - 25) * 1.25)
    health = clamp(58 + (summary.pnl_24h_pct or 0) * 2 + diversification * .25)
    volatility = clamp(sum(abs(p.pnl_24h_pct or 0) * p.allocation_pct / 100 for p in summary.positions) * 4 + largest * .35)
    risk_value = clamp(largest * .55 + volatility * .45)
    exposure = max(summary.positions, key=lambda p: p.allocation_pct, default=None)
    reduce = "Réduire progressivement la concentration sur l'actif principal." if largest > 50 else "Conserver une exposition équilibrée et surveiller la volatilité."
    improve = "Renforcer les actifs avec momentum positif confirmé, sans augmenter le risque global."
    st.markdown(
        f"<div class='card'><div class='metric'>"
        f"<div><span class='muted'>Santé du portefeuille</span><b>{health:.0f} % · {_status_positive(health)}</b></div>"
        f"<div><span class='muted'>Diversification</span><b>{diversification:.0f} % · {_status_positive(diversification)}</b></div>"
        f"<div><span class='muted'>Risque</span><b>{risk_value:.0f} % · {_status_risk(risk_value)}</b></div>"
        f"<div><span class='muted'>Volatilité</span><b>{volatility:.0f} % · {_status_risk(volatility)}</b></div>"
        f"<div><span class='muted'>Exposition principale</span><b>{html.escape(exposure.asset if exposure else 'Indisponible')}</b></div>"
        f"<div><span class='muted'>Suggestions pour réduire le risque</span><b>{html.escape(reduce)}</b></div>"
        f"<div><span class='muted'>Suggestions pour améliorer la performance</span><b>{html.escape(improve)}</b></div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )
