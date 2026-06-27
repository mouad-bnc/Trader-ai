from __future__ import annotations

import html
import math
from typing import Iterable

import pandas as pd
import streamlit as st

from portfolio_analytics import (
    enrich_portfolio,
    format_money,
    format_pct,
    recommendation_for,
    triggered_alerts,
)
from coingecko import DEFAULT_COINS, CoinGeckoClient, MarketCoin, markets_to_frame
from portfolio_io import empty_portfolio, normalize_portfolio, parse_binance_spot_csv

APP_NAME = "Trader AI"
APP_VERSION = "2.0"
GOLD = "#f6c85f"

st.set_page_config(page_title=f"{APP_NAME} {APP_VERSION}", page_icon="✦", layout="centered", initial_sidebar_state="collapsed")


def pct_class(value: float) -> str:
    return "positive" if value >= 0 else "negative"


def sparkline_svg(values: Iterable[float], stroke: str = GOLD) -> str:
    points = [float(v) for v in values if isinstance(v, int | float) and math.isfinite(float(v))]
    if len(points) < 2:
        points = [1, 1.01, 1.0, 1.02, 1.015, 1.03]
    sample = points[-36:]
    low, high = min(sample), max(sample)
    spread = high - low or 1
    coords = []
    for index, value in enumerate(sample):
        x = index * (120 / (len(sample) - 1))
        y = 44 - ((value - low) / spread * 38) + 3
        coords.append(f"{x:.1f},{y:.1f}")
    fill_path = f"M {' L '.join(coords)} L 120,52 L 0,52 Z"
    return (
        "<svg class='sparkline' viewBox='0 0 120 56' preserveAspectRatio='none' aria-hidden='true'>"
        f"<path d='{fill_path}' fill='url(#goldFade)' opacity='.45'></path>"
        f"<polyline points='{' '.join(coords)}' fill='none' stroke='{stroke}' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'></polyline>"
        "<defs><linearGradient id='goldFade' x1='0' y1='0' x2='0' y2='1'><stop offset='0%' stop-color='#f6c85f'/><stop offset='100%' stop-color='#f6c85f' stop-opacity='0'/></linearGradient></defs>"
        "</svg>"
    )


def coin_logo(coin: MarketCoin | None, symbol: str) -> str:
    if coin and coin.image:
        return f"<img class='coin-logo' src='{html.escape(coin.image)}' alt='{html.escape(symbol)} logo'>"
    return f"<div class='coin-fallback'>{html.escape(symbol[:1] or '✦')}</div>"


def score_badge(score: int) -> str:
    label = "Prime" if score >= 75 else "Strong" if score >= 60 else "Neutral" if score >= 45 else "Risk"
    return f"<span class='score-badge'><b>{score}</b><small>{label}</small></span>"


def render_market_card(coin: MarketCoin, owned_value: float = 0) -> None:
    rec = recommendation_for(coin)
    rank = f"#{coin.market_cap_rank}" if coin.market_cap_rank else "—"
    st.markdown(
        f"""
        <article class="coin-card float-in">
          <div class="coin-row">
            <div class="coin-title">{coin_logo(coin, coin.symbol)}<div><h3>{html.escape(coin.name)}</h3><p>{html.escape(coin.symbol)} · Rank {rank}</p></div></div>
            <div class="price-stack"><strong>{format_money(coin.current_price)}</strong><span class="{pct_class(coin.price_change_24h_pct)}">{format_pct(coin.price_change_24h_pct)}</span></div>
          </div>
          {sparkline_svg(coin.sparkline)}
          <div class="metric-grid"><span>7D <b class="{pct_class(coin.price_change_7d_pct)}">{format_pct(coin.price_change_7d_pct)}</b></span><span>30D <b class="{pct_class(coin.price_change_30d_pct)}">{format_pct(coin.price_change_30d_pct)}</b></span><span>Volume <b>{format_money(coin.total_volume)}</b></span></div>
          <div class="ai-strip"><div>{score_badge(rec.opportunity_score)}</div><p>{html.escape(rec.rationale)}</p></div>
          {f'<div class="owned-chip">Holding value {format_money(owned_value)}</div>' if owned_value else ''}
        </article>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
<style>
:root{--gold:#f6c85f;--gold2:#ffdf8a;--bg:#05060b;--panel:rgba(17,22,34,.72);--line:rgba(255,255,255,.10);--muted:#93a0b5;--green:#37d994;--red:#ff6b7a;}
.stApp{background:radial-gradient(circle at 15% -5%,rgba(246,200,95,.24),transparent 28%),radial-gradient(circle at 95% 5%,rgba(90,110,255,.18),transparent 30%),linear-gradient(180deg,#080a12 0%,#05060b 100%);color:#f7f8fb;}
.block-container{max-width:430px!important;padding:5.8rem .8rem 6.4rem!important;}
#MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="stDecoration"],.stDeployButton{display:none!important;}
[data-testid="stSidebar"]{background:#070912;}
.app-shell:before{content:"";position:fixed;inset:0;pointer-events:none;background:linear-gradient(120deg,transparent,rgba(255,255,255,.035),transparent);animation:sheen 7s linear infinite;z-index:0}.sticky-header{position:fixed;top:0;left:50%;transform:translateX(-50%);z-index:999;width:min(430px,100vw);padding:.8rem .9rem .7rem;background:rgba(5,6,11,.78);backdrop-filter:blur(22px);border-bottom:1px solid var(--line)}
.brand-row,.balance-row,.coin-row,.coin-title,.action-row{display:flex;align-items:center;justify-content:space-between;gap:.75rem}.brand{font-weight:800;letter-spacing:-.04em}.edu{font-size:.63rem;color:#201500;background:linear-gradient(135deg,var(--gold),var(--gold2));border-radius:999px;padding:.22rem .5rem;font-weight:800}.balance-label{color:var(--muted);font-size:.68rem}.balance{font-size:1.75rem;line-height:1;font-weight:850;letter-spacing:-.055em}.pnl-pill,.owned-chip{border:1px solid rgba(55,217,148,.3);background:rgba(55,217,148,.12);color:#b8ffd9;border-radius:999px;padding:.28rem .55rem;font-size:.72rem}.hero-card,.coin-card,.buy-card,.glass-card{background:linear-gradient(145deg,rgba(255,255,255,.105),rgba(255,255,255,.035));border:1px solid var(--line);box-shadow:0 20px 60px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.12);backdrop-filter:blur(18px);border-radius:28px;padding:1rem;margin:.75rem 0;overflow:hidden}.hero-card{background:radial-gradient(circle at 20% 0%,rgba(246,200,95,.22),transparent 42%),linear-gradient(145deg,rgba(255,255,255,.11),rgba(255,255,255,.04))}.hero-card h1{font-size:1.95rem;letter-spacing:-.07em;line-height:.95;margin:.45rem 0}.hero-card p,.ai-strip p,.muted{color:var(--muted);font-size:.78rem;margin:.25rem 0}.quick-grid,.metric-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.55rem}.mini-stat{background:rgba(0,0,0,.22);border:1px solid var(--line);border-radius:18px;padding:.7rem}.mini-stat span,.metric-grid span{display:block;color:var(--muted);font-size:.65rem}.mini-stat b,.metric-grid b{font-size:.8rem}.coin-logo,.coin-fallback{width:38px;height:38px;border-radius:50%;box-shadow:0 0 0 1px rgba(255,255,255,.12)}.coin-fallback{display:grid;place-items:center;background:linear-gradient(135deg,var(--gold),#8d6b20);color:#111;font-weight:900}.coin-title{justify-content:flex-start}.coin-title h3{font-size:.96rem;margin:0;letter-spacing:-.035em}.coin-title p,.price-stack span{margin:0;color:var(--muted);font-size:.7rem}.price-stack{text-align:right}.price-stack strong{font-size:.92rem}.positive{color:var(--green)!important}.negative{color:var(--red)!important}.sparkline{width:100%;height:58px;margin:.55rem 0}.ai-strip{display:flex;gap:.7rem;align-items:center;border-top:1px solid var(--line);padding-top:.7rem;margin-top:.65rem}.score-badge{min-width:62px;height:42px;border-radius:16px;display:flex;align-items:center;justify-content:center;gap:.18rem;flex-direction:column;background:linear-gradient(135deg,var(--gold),#70521d);color:#0c0a05;box-shadow:0 10px 30px rgba(246,200,95,.18)}.score-badge b{font-size:1rem}.score-badge small{font-size:.57rem;font-weight:800;text-transform:uppercase}.buy-card{border-color:rgba(246,200,95,.38);background:radial-gradient(circle at top right,rgba(246,200,95,.26),transparent 40%),linear-gradient(145deg,rgba(255,255,255,.12),rgba(255,255,255,.04))}.buy-card h2{font-size:1.45rem;margin:.2rem 0;letter-spacing:-.06em}.progress{height:8px;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden}.progress i{display:block;height:100%;background:linear-gradient(90deg,#8f6b21,var(--gold),#fff1b8);border-radius:999px}div[role="radiogroup"]{position:fixed;left:50%;bottom:.55rem;transform:translateX(-50%);z-index:1000;width:min(410px,calc(100vw - 18px));display:grid!important;grid-template-columns:repeat(5,1fr);gap:.25rem;background:rgba(10,12,20,.82);border:1px solid var(--line);backdrop-filter:blur(22px);border-radius:24px;padding:.35rem}div[role="radiogroup"] label{justify-content:center;border-radius:18px;padding:.4rem .1rem!important;margin:0!important;min-height:48px;background:transparent}div[role="radiogroup"] label:has(input:checked){background:linear-gradient(135deg,rgba(246,200,95,.22),rgba(255,255,255,.08))}div[role="radiogroup"] p{font-size:.62rem!important;color:#d6d9e2!important}div[role="radiogroup"] [data-testid="stMarkdownContainer"] p:before{display:block;font-size:1rem;line-height:1.05}.stButton>button,.stDownloadButton>button{border-radius:18px!important;border:1px solid rgba(246,200,95,.35)!important;background:linear-gradient(135deg,rgba(246,200,95,.22),rgba(255,255,255,.06))!important;color:#fff!important;min-height:44px}.stTextInput input,.stNumberInput input,.stTextArea textarea,.stSelectbox div[data-baseweb="select"]{border-radius:16px!important;background:rgba(255,255,255,.06)!important;border-color:var(--line)!important;color:#fff!important}.float-in{animation:floatIn .55s ease both}@keyframes floatIn{from{opacity:0;transform:translateY(12px) scale(.98)}to{opacity:1;transform:none}}@keyframes sheen{from{transform:translateX(-100%)}to{transform:translateX(100%)}}@media (min-width:700px){.sticky-header{border-radius:0 0 28px 28px}div[role="radiogroup"]{bottom:1rem}.block-container{border-left:1px solid var(--line);border-right:1px solid var(--line)}}
</style><div class="app-shell"></div>
""",
    unsafe_allow_html=True,
)

client = CoinGeckoClient()
if "portfolio" not in st.session_state:
    st.session_state.portfolio = empty_portfolio()
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["bitcoin", "ethereum", "solana"]
if "screen" not in st.session_state:
    st.session_state.screen = "Portfolio"

with st.sidebar:
    st.header("Data studio")
    uploaded = st.file_uploader("Import exchange Spot CSV", type=["csv"], help="Educational import only. No API keys or execution.")
    if uploaded is not None:
        try:
            imported = parse_binance_spot_csv(uploaded)
            if st.button("Use imported portfolio", type="primary", use_container_width=True):
                st.session_state.portfolio = imported
                st.success(f"Imported {len(imported)} assets.")
        except Exception as exc:
            st.error(str(exc))
    st.divider()
    base_ids = set(st.session_state.portfolio.get("coin_id", pd.Series(dtype=str)).dropna().astype(str))
    default_ids = ", ".join(dict.fromkeys([*DEFAULT_COINS, *st.session_state.watchlist, *base_ids]))
    coin_ids_text = st.text_area("CoinGecko IDs", value=default_ids, height=120)
    include_trending = st.toggle("Include trending", value=True)
    refresh = st.button("Refresh market data", use_container_width=True)

coin_ids = [coin.strip().lower() for coin in coin_ids_text.replace("\n", ",").split(",") if coin.strip()]
if include_trending:
    try:
        coin_ids.extend(client.trending_ids())
    except RuntimeError as exc:
        st.sidebar.warning(str(exc))
coin_ids = list(dict.fromkeys(coin_ids))

@st.cache_data(ttl=90, show_spinner=False)
def load_markets(ids: tuple[str, ...]) -> pd.DataFrame:
    return markets_to_frame(client.fetch_markets(ids))

try:
    if refresh:
        load_markets.clear()
    market_df = load_markets(tuple(coin_ids))
except RuntimeError as exc:
    st.error(str(exc)); st.stop()
if market_df.empty:
    st.warning("Add valid CoinGecko IDs to begin."); st.stop()
market_objects = [MarketCoin(**row.to_dict()) for _, row in market_df.iterrows()]
market_lookup = {coin.coin_id: coin for coin in market_objects}
market_ids = [coin.coin_id for coin in market_objects]

st.session_state.portfolio = normalize_portfolio(st.session_state.portfolio)
portfolio = enrich_portfolio(st.session_state.portfolio, market_objects)
total_value = float(portfolio["value"].sum()) if not portfolio.empty else 0.0
total_cost = float(portfolio["cost_basis"].sum()) if not portfolio.empty else 0.0
total_pnl = total_value - total_cost
total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0.0
best_market = max(market_objects, key=lambda coin: recommendation_for(coin).opportunity_score)
best_rec = recommendation_for(best_market)
alerts = triggered_alerts(st.session_state.portfolio, market_objects)

st.markdown(f"""
<header class="sticky-header">
  <div class="brand-row"><div class="brand">✦ {APP_NAME}</div><div class="edu">EDUCATIONAL ONLY</div></div>
  <div class="balance-row"><div><div class="balance-label">Portfolio balance</div><div class="balance">{format_money(total_value)}</div></div><div class="pnl-pill {pct_class(total_pnl_pct)}">{format_money(total_pnl)} · {format_pct(total_pnl_pct)}</div></div>
</header>
""", unsafe_allow_html=True)

screen = st.radio("Navigation", ["Portfolio", "Markets", "Watchlist", "AI", "Settings"], horizontal=True, label_visibility="collapsed", key="screen")

st.markdown(f"""
<section class="hero-card float-in"><span class="muted">Premium crypto intelligence · no custody · no execution</span><h1>Mobile market cockpit for smarter learning.</h1><p>Custom cards, public CoinGecko data, deterministic AI-style scoring, alerts, watchlists, and portfolio education in a dark gold interface.</p><div class="quick-grid"><div class="mini-stat"><span>Assets</span><b>{len(portfolio)}</b></div><div class="mini-stat"><span>Alerts</span><b>{len(alerts)}</b></div><div class="mini-stat"><span>Top score</span><b>{best_rec.symbol} {best_rec.opportunity_score}</b></div></div></section>
""", unsafe_allow_html=True)

if screen == "Portfolio":
    if not alerts.empty:
        for _, alert in alerts.iterrows():
            st.markdown(f"<div class='glass-card'>⚡ <b>{html.escape(str(alert['Asset']))}</b> {html.escape(str(alert['Alert']))} at {format_money(float(alert['Price']))}</div>", unsafe_allow_html=True)
    with st.expander("Add or update holding", expanded=portfolio.empty):
        with st.form("holding_form", clear_on_submit=False):
            coin_id = st.selectbox("Asset", options=market_ids, format_func=lambda cid: f"{market_lookup[cid].name} ({market_lookup[cid].symbol})")
            quantity = st.number_input("Quantity", min_value=0.0, step=0.0001, format="%.8f")
            avg_cost = st.number_input("Average cost", min_value=0.0, step=1.0, format="%.4f")
            c1, c2 = st.columns(2)
            alert_below = c1.number_input("Alert below", min_value=0.0, step=1.0, format="%.4f")
            alert_above = c2.number_input("Alert above", min_value=0.0, step=1.0, format="%.4f")
            favorite = st.toggle("Add to favorites", value=True)
            notes = st.text_input("Notes", placeholder="Strategy, thesis, or reminder")
            if st.form_submit_button("Save holding", use_container_width=True):
                coin = market_lookup[coin_id]
                next_row = pd.DataFrame([{"coin_id": coin_id, "symbol": coin.symbol, "quantity": quantity, "avg_cost": avg_cost, "alert_below": alert_below, "alert_above": alert_above, "favorite": favorite, "notes": notes}])
                current = st.session_state.portfolio[st.session_state.portfolio["coin_id"] != coin_id]
                st.session_state.portfolio = normalize_portfolio(pd.concat([current, next_row], ignore_index=True))
                st.rerun()
    st.download_button("Export portfolio CSV", st.session_state.portfolio.to_csv(index=False), "trader_ai_portfolio.csv", "text/csv", use_container_width=True)
    for _, row in portfolio.iterrows():
        coin = market_lookup.get(row["coin_id"])
        render_market_card(coin, float(row["value"])) if coin else None
        st.markdown(f"<div class='progress'><i style='width:{min(100, float(row['allocation_pct'])):.1f}%'></i></div><p class='muted'>Allocation {row['allocation_pct']:.2f}% · P&L {format_money(float(row['pnl']))} ({'—' if pd.isna(row['pnl_pct']) else format_pct(float(row['pnl_pct']))})</p>", unsafe_allow_html=True)
        if st.button(f"Remove {row['symbol']}", key=f"remove_{row['coin_id']}", use_container_width=True):
            st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio["coin_id"] != row["coin_id"]]
            st.rerun()

elif screen == "Markets":
    for coin in market_objects:
        render_market_card(coin)

elif screen == "Watchlist":
    picks = st.multiselect("Curate watchlist", options=market_ids, default=[x for x in st.session_state.watchlist if x in market_ids], format_func=lambda cid: f"{market_lookup[cid].name} ({market_lookup[cid].symbol})")
    st.session_state.watchlist = picks
    fav_ids = set(st.session_state.portfolio.loc[st.session_state.portfolio["favorite"], "coin_id"]) if not st.session_state.portfolio.empty else set()
    for cid in dict.fromkeys([*picks, *fav_ids]):
        if cid in market_lookup:
            render_market_card(market_lookup[cid])

elif screen == "AI":
    recommendations = sorted((recommendation_for(coin) for coin in market_objects), key=lambda rec: rec.opportunity_score, reverse=True)
    for rec in recommendations[:5]:
        coin = market_lookup[rec.coin_id]
        st.markdown(f"<section class='buy-card float-in'><div class='action-row'><div>{coin_logo(coin, rec.symbol)}<h2>BUY OPPORTUNITY</h2><p class='muted'>{html.escape(rec.name)} · {html.escape(rec.symbol)}</p></div>{score_badge(rec.opportunity_score)}</div><div class='progress'><i style='width:{rec.opportunity_score}%'></i></div><p>{html.escape(rec.action)}</p><p class='muted'>{html.escape(rec.rationale)} This is an educational rubric, not financial advice.</p>{sparkline_svg(coin.sparkline)}</section>", unsafe_allow_html=True)

else:
    st.markdown("<section class='glass-card'><h3>Settings</h3><p class='muted'>This app uses public market data, local Streamlit session state, and educational analytics only. It cannot connect to exchange accounts, custody assets, or place trades.</p></section>", unsafe_allow_html=True)
    st.caption(f"{APP_NAME} v{APP_VERSION} · Dark gold mobile UI · Original design")
