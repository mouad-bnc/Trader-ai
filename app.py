from __future__ import annotations

import html
import math

import pandas as pd
import streamlit as st

from analytics import enrich_portfolio, format_money, format_pct, recommendation_for
from coingecko import DEFAULT_COINS, CoinGeckoClient, MarketCoin, markets_to_frame
from sample_data import default_portfolio

APP_NAME = "Trader AI"
APP_VERSION = "0.2"


def pnl_class(value: float) -> str:
    return "gain" if value >= 0 else "loss"


def safe_pct(value: float) -> str:
    if pd.isna(value) or math.isinf(value):
        return "—"
    return format_pct(float(value))


def money_compact(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.2f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    if abs_value >= 1_000:
        return f"${value / 1_000:,.2f}K"
    return format_money(value)


st.set_page_config(page_title=f"{APP_NAME} {APP_VERSION}", page_icon="🟢", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
    :root {
      --bg: #070b10;
      --panel: rgba(15, 23, 42, .86);
      --panel-strong: rgba(15, 23, 42, .96);
      --line: rgba(148, 163, 184, .18);
      --muted: #94a3b8;
      --text: #f8fafc;
      --green: #22c55e;
      --green-soft: rgba(34, 197, 94, .16);
      --red: #ef4444;
      --red-soft: rgba(239, 68, 68, .14);
      --yellow: #f59e0b;
    }
    html, body, [data-testid="stAppViewContainer"] {background: radial-gradient(circle at top, rgba(34,197,94,.10), transparent 34rem), var(--bg); color: var(--text);}
    .block-container {padding: 1rem .9rem 6rem; max-width: 430px;}
    header[data-testid="stHeader"] {background: transparent;}
    section[data-testid="stSidebar"] {background: #0b111c; border-right: 1px solid var(--line);}
    [data-testid="stMetric"] {background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: .8rem; box-shadow: 0 10px 28px rgba(0,0,0,.25);}
    [data-testid="stMetricLabel"] {color: var(--muted); font-size: .75rem;}
    [data-testid="stMetricValue"] {font-size: clamp(1.15rem, 7vw, 1.55rem);}
    [data-testid="stMetricDelta"] {font-size: .78rem;}
    div[data-testid="stHorizontalBlock"] {gap: .7rem;}
    .hero {border: 1px solid rgba(34,197,94,.25); background: linear-gradient(145deg, rgba(34,197,94,.18), rgba(15,23,42,.94) 48%, rgba(2,6,23,.96)); border-radius: 26px; padding: 1.05rem; margin-bottom: .8rem; box-shadow: 0 20px 50px rgba(0,0,0,.35);}
    .hero h1 {margin: 0 0 .35rem; font-size: clamp(1.9rem, 10vw, 2.9rem); letter-spacing: -.06em; line-height: .95;}
    .hero p {color: #cbd5e1; margin: 0; font-size: .94rem; line-height: 1.45;}
    .pill {display: inline-flex; align-items: center; gap: .35rem; padding: .28rem .7rem; border-radius: 999px; background: var(--green-soft); color: #86efac; font-size: .75rem; margin-bottom: .75rem; border: 1px solid rgba(34,197,94,.22);}
    .mobile-section {scroll-margin-top: 1rem;}
    .summary-card, .asset-card, .market-card, .rec-card {background: var(--panel); border: 1px solid var(--line); border-radius: 20px; padding: .9rem; margin: .65rem 0; box-shadow: 0 12px 34px rgba(0,0,0,.22);}
    .summary-card {background: linear-gradient(135deg, rgba(34,197,94,.18), rgba(15,23,42,.92));}
    .summary-top, .card-row, .market-head, .bottom-nav {display: flex; align-items: center; justify-content: space-between; gap: .75rem;}
    .summary-label, .muted {color: var(--muted); font-size: .78rem;}
    .summary-value {font-size: 2rem; font-weight: 800; letter-spacing: -.04em; margin-top: .15rem;}
    .gain {color: var(--green) !important;}
    .loss {color: var(--red) !important;}
    .chip {border-radius: 999px; padding: .28rem .55rem; font-size: .72rem; font-weight: 700; background: rgba(148,163,184,.12); color: #e2e8f0; white-space: nowrap;}
    .chip.gain {background: var(--green-soft); color: #86efac !important;}
    .chip.loss {background: var(--red-soft); color: #fca5a5 !important;}
    .asset-title, .market-title {font-size: 1rem; font-weight: 800; letter-spacing: -.02em;}
    .asset-symbol {color: #86efac; font-size: .78rem; font-weight: 800;}
    .price {font-size: 1.15rem; font-weight: 800;}
    .grid-2 {display: grid; grid-template-columns: 1fr 1fr; gap: .55rem; margin-top: .75rem;}
    .stat {background: rgba(2,6,23,.38); border: 1px solid var(--line); border-radius: 14px; padding: .58rem; min-width: 0;}
    .stat b {display: block; font-size: .9rem; margin-top: .1rem; overflow-wrap: anywhere;}
    .bottom-nav {position: fixed; left: 50%; bottom: .75rem; transform: translateX(-50%); width: min(390px, calc(100vw - 1.25rem)); z-index: 999; background: rgba(2,6,23,.92); backdrop-filter: blur(16px); border: 1px solid rgba(34,197,94,.24); border-radius: 999px; padding: .35rem; box-shadow: 0 18px 45px rgba(0,0,0,.5);}
    .bottom-nav a {flex: 1; text-align: center; color: #cbd5e1 !important; text-decoration: none; font-size: .72rem; font-weight: 800; padding: .62rem .3rem; border-radius: 999px;}
    .bottom-nav a:first-child {background: var(--green-soft); color: #86efac !important;}
    .sticky-action {position: sticky; top: .55rem; z-index: 50; margin-bottom: .75rem;}
    .stButton > button {min-height: 48px; border-radius: 999px; font-weight: 800; border: 1px solid rgba(34,197,94,.35);}
    .stDataFrame, [data-testid="stDataFrame"], [data-testid="stDataEditor"] {border-radius: 18px; overflow: hidden; border: 1px solid var(--line);}
    h2, h3 {letter-spacing: -.035em;}
    @media (min-width: 700px) {.block-container {max-width: 1180px; padding-left: 2rem; padding-right: 2rem;} .card-grid {display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: .8rem;} .bottom-nav {width: 430px;} }
    @media (max-width: 430px) { .block-container {max-width: 390px;} h2 {font-size: 1.25rem;} .summary-value {font-size: 1.75rem;} .grid-2 {gap: .45rem;} }
    @media (max-width: 390px) { .block-container {padding-left: .75rem; padding-right: .75rem;} .hero {padding: .9rem;} .market-card, .asset-card, .summary-card, .rec-card {padding: .8rem;} }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <nav class="bottom-nav" aria-label="Mobile app navigation">
      <a href="#portfolio">Portfolio</a>
      <a href="#markets">Markets</a>
      <a href="#signals">Signals</a>
      <a href="#settings">Setup</a>
    </nav>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <section class="hero">
      <span class="pill">🟢 {APP_NAME} · v{APP_VERSION} · CoinGecko only</span>
      <h1>Mobile crypto command center</h1>
      <p>Track a manual portfolio, monitor public market data, and learn from educational signals without exchange keys or trading execution.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

client = CoinGeckoClient()

with st.sidebar:
    st.header("Market universe")
    st.caption("Use CoinGecko coin IDs, not ticker pairs. Example: bitcoin, ethereum, solana.")
    default_ids = ", ".join(DEFAULT_COINS)
    coin_ids_text = st.text_area("CoinGecko IDs", value=default_ids, height=120)
    include_trending = st.toggle("Include CoinGecko trending coins", value=True)
    refresh = st.button("Refresh market data", type="primary", use_container_width=True)
    st.divider()
    st.caption("No Binance API · No API keys · No trading execution · Educational analysis only")

with st.container():
    st.markdown('<div id="settings" class="sticky-action mobile-section">', unsafe_allow_html=True)
    refresh_top = st.button("↻ Refresh public market data", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

coin_ids = [coin.strip().lower() for coin in coin_ids_text.replace("\n", ",").split(",") if coin.strip()]
if include_trending:
    try:
        coin_ids.extend(client.trending_ids())
    except RuntimeError as exc:
        st.sidebar.warning(str(exc))
coin_ids = list(dict.fromkeys(coin_ids))


@st.cache_data(ttl=90, show_spinner=False)
def load_markets(ids: tuple[str, ...]) -> pd.DataFrame:
    markets = client.fetch_markets(ids)
    return markets_to_frame(markets)


try:
    if refresh or refresh_top:
        load_markets.clear()
    market_df = load_markets(tuple(coin_ids))
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

if market_df.empty:
    st.warning("Add at least one valid CoinGecko coin ID to begin.")
    st.stop()

market_objects = [MarketCoin(**row.to_dict()) for _, row in market_df.iterrows()]
market_ids = [coin.coin_id for coin in market_objects]

if "portfolio" not in st.session_state:
    st.session_state.portfolio = default_portfolio()

portfolio = enrich_portfolio(st.session_state.portfolio, market_objects)
total_value = float(portfolio["value"].sum()) if not portfolio.empty else 0.0
total_cost = float(portfolio["cost_basis"].sum()) if not portfolio.empty else 0.0
total_pnl = total_value - total_cost
total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0.0
best_market = max(market_objects, key=lambda coin: recommendation_for(coin).opportunity_score)
best_rec = recommendation_for(best_market)

st.markdown('<section id="portfolio" class="mobile-section">', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="summary-card">
      <div class="summary-top"><span class="summary-label">Portfolio value</span><span class="chip {pnl_class(total_pnl)}">{format_pct(total_pnl_pct)} P&L</span></div>
      <div class="summary-value">{format_money(total_value)}</div>
      <div class="card-row"><span class="muted">Unrealized P&L</span><strong class="{pnl_class(total_pnl)}">{format_money(total_pnl)}</strong></div>
      <div class="card-row"><span class="muted">Tracked markets</span><strong>{len(market_objects)}</strong></div>
      <div class="card-row"><span class="muted">Top opportunity</span><strong>{html.escape(best_rec.symbol)} · {best_rec.opportunity_score}/100</strong></div>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_cols = st.columns(2)
metric_cols[0].metric("Portfolio value", format_money(total_value))
metric_cols[1].metric("Unrealized P&L", format_money(total_pnl), format_pct(total_pnl_pct))

st.subheader("Manual portfolio")
st.caption("Edit quantities and average costs locally. Nothing is sent to an exchange.")
portfolio_input = st.data_editor(
    st.session_state.portfolio,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "coin_id": st.column_config.SelectboxColumn("Coin", options=market_ids, required=True),
        "quantity": st.column_config.NumberColumn("Qty", min_value=0.0, step=0.0001, format="%.8f"),
        "avg_cost": st.column_config.NumberColumn("Avg cost", min_value=0.0, step=1.0, format="$%.4f"),
    },
    hide_index=True,
)
st.session_state.portfolio = portfolio_input
portfolio = enrich_portfolio(portfolio_input, market_objects)

st.subheader("Holdings")
if portfolio.empty:
    st.info("Add holdings to see mobile portfolio cards.")
else:
    st.markdown('<div class="card-grid">', unsafe_allow_html=True)
    for _, row in portfolio.iterrows():
        pnl = float(row["pnl"])
        st.markdown(
            f"""
            <article class="asset-card">
              <div class="card-row"><div><div class="asset-title">{html.escape(str(row['name']))}</div><div class="asset-symbol">{html.escape(str(row['symbol']))}</div></div><span class="chip {pnl_class(pnl)}">{safe_pct(float(row['pnl_pct']))}</span></div>
              <div class="grid-2">
                <div class="stat"><span class="muted">Value</span><b>{format_money(float(row['value']))}</b></div>
                <div class="stat"><span class="muted">P&L</span><b class="{pnl_class(pnl)}">{format_money(pnl)}</b></div>
                <div class="stat"><span class="muted">Price</span><b>{format_money(float(row['current_price']))}</b></div>
                <div class="stat"><span class="muted">Allocation</span><b>{float(row['allocation_pct']):.1f}%</b></div>
              </div>
            </article>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</section>", unsafe_allow_html=True)

st.markdown('<section id="signals" class="mobile-section">', unsafe_allow_html=True)
st.subheader("Educational signals")
recommendations = [recommendation_for(coin) for coin in market_objects]
for rec in sorted(recommendations, key=lambda item: item.opportunity_score, reverse=True)[:6]:
    tone = "gain" if rec.opportunity_score >= 60 else "loss" if rec.opportunity_score < 45 else ""
    st.markdown(
        f"""
        <article class="rec-card">
          <div class="card-row"><div><div class="asset-title">{html.escape(rec.name)}</div><div class="muted">{html.escape(rec.symbol)} · {html.escape(rec.action)}</div></div><span class="chip {tone}">{rec.opportunity_score}/100</span></div>
          <p class="muted" style="margin:.65rem 0 0;">{html.escape(rec.rationale)}</p>
        </article>
        """,
        unsafe_allow_html=True,
    )
st.markdown("</section>", unsafe_allow_html=True)

st.markdown('<section id="markets" class="mobile-section">', unsafe_allow_html=True)
st.subheader("Markets")
st.markdown('<div class="card-grid">', unsafe_allow_html=True)
for coin in market_objects:
    change = coin.price_change_24h_pct
    st.markdown(
        f"""
        <article class="market-card">
          <div class="market-head"><div><div class="market-title">{html.escape(coin.name)}</div><div class="muted">{html.escape(coin.symbol)} · Rank #{coin.market_cap_rank or '—'}</div></div><span class="chip {pnl_class(change)}">24h {format_pct(change)}</span></div>
          <div class="price">{format_money(coin.current_price)}</div>
          <div class="grid-2">
            <div class="stat"><span class="muted">7d</span><b class="{pnl_class(coin.price_change_7d_pct)}">{format_pct(coin.price_change_7d_pct)}</b></div>
            <div class="stat"><span class="muted">30d</span><b class="{pnl_class(coin.price_change_30d_pct)}">{format_pct(coin.price_change_30d_pct)}</b></div>
            <div class="stat"><span class="muted">Volume</span><b>{money_compact(coin.total_volume)}</b></div>
            <div class="stat"><span class="muted">Mkt cap</span><b>{money_compact(coin.market_cap)}</b></div>
          </div>
        </article>
        """,
        unsafe_allow_html=True,
    )
st.markdown("</div></section>", unsafe_allow_html=True)

st.caption("Disclaimer: Trader AI is educational only and is not financial advice. It uses public CoinGecko data, no Binance API, no API keys, and no trading execution.")
