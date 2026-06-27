from __future__ import annotations

import html
from typing import Callable

import pandas as pd
import streamlit as st

from coingecko import MarketCoin
from portfolio_analytics import format_money, format_pct, recommendation_for


def coin_logo(coin: MarketCoin | None, symbol: str) -> str:
    if coin and coin.image:
        return f"<img class='coin-logo' src='{html.escape(coin.image)}' alt='{html.escape(symbol)} logo'>"
    return f"<div class='coin-fallback'>{html.escape(symbol[:1] or '✦')}</div>"


def render_market_card(
    coin: MarketCoin,
    *,
    owned_value: float = 0,
    favorite: bool = False,
    pct_class: Callable[[float], str],
    sparkline_svg: Callable[..., str],
    risk_label: Callable[[MarketCoin], tuple[str, str]],
    ai_badge: Callable[[int], str],
    confidence_for: Callable[[MarketCoin], int],
    volatility_pct: Callable[[MarketCoin], float],
    safe_width: Callable[[float], int],
) -> None:
    rec = recommendation_for(coin)
    risk, risk_class = risk_label(coin)
    rank = f"#{coin.market_cap_rank}" if coin.market_cap_rank else "—"
    heart = "♥" if favorite else "♡"
    trend_arrow = "↗" if coin.price_change_24h_pct >= 0 else "↘"
    vol = volatility_pct(coin)
    confidence = confidence_for(coin)
    st.markdown(
        f"""
        <article class="coin-card float-in">
          <div class="coin-row">
            <div class="coin-title">{coin_logo(coin, coin.symbol)}<div><h3>{html.escape(coin.name)}</h3><p>{html.escape(coin.symbol)} · Rang {rank}</p></div></div>
            <div class="price-stack"><button class="fav" aria-label="favori">{heart}</button><strong>{format_money(coin.current_price)}</strong><span class="{pct_class(coin.price_change_24h_pct)}">{trend_arrow} 24h {format_pct(coin.price_change_24h_pct)}</span></div>
          </div>
          {sparkline_svg(coin.sparkline, '#02C076' if coin.price_change_7d_pct >= 0 else '#F6465D')}
          <div class="metric-grid"><span>IA <b>{ai_badge(rec.opportunity_score)}</b></span><span>Risque <b class="{risk_class}">{risk}</b></span><span>Confiance <b>{confidence}%</b></span></div>
          <div class="volatility"><i style="width:{safe_width(vol * 4)}%"></i></div>
          <div class="badge-row"><em>{trend_arrow} Tendance</em><em>Volatilité {vol:.1f}%</em>{f'<em>Position {format_money(owned_value)}</em>' if owned_value else ''}</div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_holding_card(row: pd.Series, coin: MarketCoin | None, *, pct_class: Callable[[float], str], sparkline_svg: Callable[..., str]) -> None:
    pnl = float(row.get("pnl") or 0)
    daily = coin.price_change_24h_pct if coin else 0
    st.markdown(f"""<article class='coin-card holding-card'>
      <div class='coin-row'><div class='coin-title'>{coin_logo(coin, str(row['symbol']))}<div><h3>{html.escape(str(row['name']))}</h3><p>{float(row['quantity']):,.8f} {html.escape(str(row['symbol']))}</p></div></div><div class='price-stack'><strong>{format_money(float(row['value']))}</strong><span class='{pct_class(pnl)}'>{format_money(pnl)} · {format_pct(float(row['pnl_pct'])) if not pd.isna(row['pnl_pct']) else '—'}</span></div></div>
      {sparkline_svg(coin.sparkline if coin else [], '#02C076' if daily >= 0 else '#F6465D')}
      <div class='metric-grid'><span>Prix moyen <b>{format_money(float(row['avg_cost']))}</b></span><span>Journalier <b class='{pct_class(daily)}'>{format_pct(daily)}</b></span><span>Allocation <b>{format_pct(float(row['allocation_pct']))}</b></span></div>
    </article>""", unsafe_allow_html=True)
