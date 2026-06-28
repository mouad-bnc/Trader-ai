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
        summary = bz.spot_portfolio()
        _render_binance_portfolio(summary)
    else:
        markets = cg.get_markets()
        summary = pf.summarize(pf.demo_holdings(), markets)
        _render_manual_portfolio(summary, pf)


def _render_binance_portfolio(summary: BinancePortfolioSummary) -> None:
    pnl_class = "positive" if (summary.pnl_24h_usdt or 0) >= 0 else "negative"
    pnl_label = "P&L 24h estimé indisponible"
    if summary.pnl_24h_usdt is not None and summary.pnl_24h_pct is not None:
        pnl_label = f"P&L 24h estimé {money(summary.pnl_24h_usdt)} · {percent(summary.pnl_24h_pct)}"

    st.markdown(
        f"<div class='card hero'><span class='pill'>Binance connecté en lecture seule</span>"
        f"<h2>{money(summary.total_value_usdt, 'USDT')}</h2>"
        f"<p class='{pnl_class}'>{html.escape(pnl_label)}</p>"
        f"<p class='muted'>Soldes Spot réels · Valorisation publique USDT · Aucun endpoint de trading ou retrait.</p></div>",
        unsafe_allow_html=True,
    )

    if not summary.positions:
        empty_state("Synchronisation Binance vide", "La connexion en lecture seule n'a retourné aucun solde Spot exploitable.")
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
    for pos in summary.positions:
        st.markdown(
            f"<div class='card'><div class='row'><div><h3>{html.escape(pos.holding.name)}</h3>"
            f"<p class='muted'>{pos.holding.quantity:g} {html.escape(pos.holding.symbol)}</p></div>"
            f"<div style='text-align:right'><b>{money(pos.value)}</b>"
            f"<p class='{ 'positive' if pos.pnl >= 0 else 'negative' }'>{percent(pos.pnl_pct)}</p></div></div></div>",
            unsafe_allow_html=True,
        )
    allocation_bar(pf.allocation(summary))
