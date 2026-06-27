from __future__ import annotations

import streamlit as st

from components.ui import render_empty_card
from portfolio_analytics import format_money, format_pct


def render_home(
    *,
    best_row,
    worst_row,
    portfolio,
    market_lookup,
    market_objects,
    total_value: float,
    daily_pnl: float,
    daily_pnl_pct: float,
    total_pnl: float,
    total_pnl_pct: float,
    dominance: float,
    fng_display: str,
    fng_label: str,
    pct_class,
    sparkline_svg,
    binance_configured: bool,
) -> None:
    st.markdown("<div class='hero'><p>Bonjour Mouad 👋</p><h1>Votre cockpit crypto</h1></div>", unsafe_allow_html=True)
    top_gain = best_row.iloc[0] if not best_row.empty else None
    top_loss = worst_row.iloc[0] if not worst_row.empty else None
    if portfolio.empty and not binance_configured:
        render_empty_card("⌁", "Connectez Binance pour afficher votre portefeuille.", "Vos soldes, votre allocation et votre PnL apparaîtront ici dès qu'une connexion lecture seule sera disponible.")
        if st.button("Connecter Binance", use_container_width=True):
            st.toast("Ajoutez BINANCE_API_KEY et BINANCE_API_SECRET côté serveur pour activer la synchronisation.")
    else:
        st.markdown(f"""
        <section class='portfolio-card float-in'><span class='eyebrow'>TABLEAU DE BORD</span><div class='value'>{format_money(total_value)}</div>
          <div class='quick-grid'><div class='mini-stat'><span>Variation du jour</span><b class='{pct_class(daily_pnl)}'>{format_money(daily_pnl)}<br>{format_pct(daily_pnl_pct)}</b></div><div class='mini-stat'><span>PnL global</span><b class='{pct_class(total_pnl)}'>{format_money(total_pnl)}<br>{format_pct(total_pnl_pct)}</b></div><div class='mini-stat'><span>BTC dominance</span><b>{dominance:.1f}%</b></div></div>
          {sparkline_svg([sum((market_lookup.get(str(r['coin_id'])).sparkline[i] if market_lookup.get(str(r['coin_id'])) and len(market_lookup[str(r['coin_id'])].sparkline)>i else 0)*float(r['quantity']) for _, r in portfolio.iterrows()) for i in range(0, 42)] if not portfolio.empty else [coin.current_price for coin in market_objects[:8]])}
        </section>""", unsafe_allow_html=True)
    st.markdown("<section class='glass-card mission'><h2>Mission du jour</h2><ul><li>✓ Vérifier la valeur totale</li><li>✓ Lire les alertes de marché</li><li>✓ Identifier une opportunité à surveiller</li></ul></section>", unsafe_allow_html=True)
    gain_txt = f"{top_gain['symbol']} {format_money(float(top_gain['pnl']))}" if top_gain is not None else "Ajoute une position"
    loss_txt = f"{top_loss['symbol']} {format_money(float(top_loss['pnl']))}" if top_loss is not None else "Ajoute une position"
    if portfolio.empty:
        st.markdown(f"<section class='glass-card'><div class='metric-grid'><span>Fear & Greed <b>{fng_display}<br>{fng_label}</b></span><span>BTC Dominance <b>{dominance:.1f}%</b></span><span>Top Movers <b>{len(market_objects)} suivis</b></span></div></section>", unsafe_allow_html=True)
    else:
        st.markdown(f"<section class='glass-card'><div class='quick-grid'><div class='mini-stat'><span>Spot</span><b>{format_money(total_value)}</b></div><div class='mini-stat'><span>Actifs</span><b>{len(portfolio)}</b></div><div class='mini-stat'><span>PnL</span><b class='{pct_class(total_pnl)}'>{format_pct(total_pnl_pct)}</b></div></div><div class='metric-grid'><span>Top gain <b class='positive'>{gain_txt}</b></span><span>Top perte <b class='negative'>{loss_txt}</b></span><span>Fear & Greed <b>{fng_display}<br>{fng_label}</b></span></div></section>", unsafe_allow_html=True)

