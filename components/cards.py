from __future__ import annotations

import html
import streamlit as st

from components.charts import sparkline
from services.coingecko_service import MarketAsset
from utils.helpers import money, percent


def metric_card(title: str, value: str, caption: str = "") -> None:
    st.markdown(f"<div class='card'><span class='pill'>{html.escape(title)}</span><h2>{html.escape(value)}</h2><p class='muted'>{html.escape(caption)}</p></div>", unsafe_allow_html=True)


def empty_state(title: str, message: str) -> None:
    st.markdown(f"<div class='card empty'><span class='pill soft'>État sécurisé</span><h3>{html.escape(title)}</h3><p class='muted'>{html.escape(message)}</p></div>", unsafe_allow_html=True)


def asset_card(asset: MarketAsset) -> None:
    klass = "positive" if asset.price_change_24h_pct >= 0 else "negative"
    logo = f"<img class='logo' src='{html.escape(asset.image)}'>" if asset.image else "<span class='logo pill'>✦</span>"
    st.markdown(f"<div class='card'><div class='row'><div class='row'>{logo}<div><h3>{html.escape(asset.name)}</h3><p class='muted'>{html.escape(asset.symbol)} · Rang #{asset.market_cap_rank or '—'}</p></div></div><div style='text-align:right'><b>{money(asset.current_price)}</b><p class='{klass}'>{percent(asset.price_change_24h_pct)}</p></div></div>{sparkline(asset.sparkline, asset.price_change_24h_pct >= 0)}<div class='metric'><div><span class='muted'>Cap.</span><b>{money(asset.market_cap)}</b></div><div><span class='muted'>Volume</span><b>{money(asset.total_volume)}</b></div><div><span class='muted'>7 jours</span><b class='{ 'positive' if asset.price_change_7d_pct >= 0 else 'negative' }'>{percent(asset.price_change_7d_pct)}</b></div></div></div>", unsafe_allow_html=True)
