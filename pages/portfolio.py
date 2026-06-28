from __future__ import annotations

import html

import streamlit as st
from components.charts import allocation_bar
from components.cards import empty_state
from services.binance_service import BinancePortfolioSummary, BinanceService
from services.coingecko_service import CoinGeckoService
from services.portfolio_service import PortfolioService, PortfolioSummary
from utils.helpers import money, percent


def render(services: dict[str, object]) -> None:
    cg = services["coingecko"]; pf = services["portfolio"]; bz = services["binance"]
    assert isinstance(cg, CoinGeckoService) and isinstance(pf, PortfolioService) and isinstance(bz, BinanceService)
    st.title("Portefeuille")

    if bz.configured:
        summary = bz.spot_portfolio(cg)
        _render_binance_debug_panel(summary.debug)
        if summary.connected:
            _render_binance_portfolio(summary)
        else:
            message = html.escape(summary.status_message or "Vérifiez les secrets Streamlit BINANCE_API_KEY et BINANCE_API_SECRET. Aucun secret n'est affiché.")
            st.markdown(f"<div class='card hero'><span class='pill soft'>Connexion Binance indisponible</span><p class='muted'>{message}</p></div>", unsafe_allow_html=True)
            _render_manual_portfolio(pf.summarize([]), pf)
    else:
        _render_binance_debug_panel(bz.last_debug)
        st.markdown("<div class='card hero'><span class='pill soft'>Binance non configuré</span><p class='muted'>Ajoutez BINANCE_API_KEY et BINANCE_API_SECRET aux secrets Streamlit pour afficher vos vrais soldes Spot en lecture seule.</p></div>", unsafe_allow_html=True)
        empty_state("Aucun portefeuille Binance", "Aucune donnée fictive n’est affichée : connectez Binance en lecture seule pour synchroniser vos avoirs réels.")
        _render_manual_portfolio(pf.summarize([]), pf)


def _render_binance_debug_panel(debug: dict[str, object]) -> None:
    """Temporary safe diagnostics for Binance read-only synchronization."""
    with st.expander("Réglages · debug Binance sécurisé", expanded=False):
        st.write(f"API key present: {'oui' if debug.get('api_key_present') else 'non'}")
        st.write(f"API secret present: {'oui' if debug.get('api_secret_present') else 'non'}")
        st.write(f"Binance status code: {debug.get('status_code') if debug.get('status_code') is not None else 'indisponible'}")
        st.write(f"Number of balances returned: {debug.get('balances_returned', 0)}")
        st.write(f"Number of non-zero balances: {debug.get('non_zero_balances', 0)}")
        if debug.get("error"):
            st.write(f"Erreur: {html.escape(str(debug.get('error')))}")


def _render_binance_portfolio(summary: BinancePortfolioSummary) -> None:
    pnl_class = "positive" if (summary.pnl_24h_usdt or 0) >= 0 else "negative"
    pnl_label = "P&L 24h estimé indisponible"
    if summary.pnl_24h_usdt is not None and summary.pnl_24h_pct is not None:
        pnl_label = f"P&L 24h estimé {money(summary.pnl_24h_usdt)} · {percent(summary.pnl_24h_pct)}"

    st.markdown(
        f"<div class='card hero'><span class='pill'>Binance connecté en lecture seule</span>"
        f"<h2>{money(summary.total_value_usdt, 'USDT')}</h2>"
        f"<p class='{pnl_class}'>{html.escape(pnl_label)}</p>"
        f"<p class='muted'>{html.escape(summary.status_message)}</p>"
        f"<p class='muted'>Soldes Spot réels · Valorisation publique USDT · Aucun endpoint de trading ou retrait.</p></div>",
        unsafe_allow_html=True,
    )

    if not summary.positions:
        empty_state("Aucun solde Spot", "Binance est connecté en lecture seule, mais aucun solde non nul n'a été trouvé.")
        return

    for pos in summary.positions:
        pnl_text = "P&L indisponible"
        pnl_class = "muted"
        if pos.pnl_24h_usdt is not None and pos.pnl_24h_pct is not None:
            pnl_class = "positive" if pos.pnl_24h_usdt >= 0 else "negative"
            pnl_text = f"{money(pos.pnl_24h_usdt)} · {percent(pos.pnl_24h_pct)}"
        price_text = money(pos.price_usdt, "USDT") if pos.price_usdt else "Prix USDT indisponible"
        st.markdown(
            f"<div class='card'><div class='row'><div>"
            f"<h3>{html.escape(pos.asset)}</h3>"
            f"<p class='muted'>{pos.total:g} {html.escape(pos.asset)} · Libre {pos.free:g} · Bloqué {pos.locked:g}</p>"
            f"<p class='muted'>Prix: {html.escape(price_text)} · Allocation {pos.allocation_pct:.1f}%</p>"
            f"</div><div style='text-align:right'><b>{money(pos.estimated_value_usdt, 'USDT')}</b>"
            f"<p class='{pnl_class}'>{html.escape(pnl_text)}</p></div></div></div>",
            unsafe_allow_html=True,
        )
    allocation_bar({position.asset: position.allocation_pct for position in summary.positions})


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
