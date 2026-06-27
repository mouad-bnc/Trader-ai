from __future__ import annotations

import html
import math
from typing import Iterable

import pandas as pd
import streamlit as st

from coingecko import DEFAULT_COINS, CoinGeckoClient, MarketCoin, markets_to_frame
from portfolio_analytics import enrich_portfolio, format_money, format_pct, recommendation_for, triggered_alerts
from portfolio_io import empty_portfolio, normalize_portfolio, parse_binance_spot_csv

APP_NAME = "Trader AI"
APP_VERSION = "3.0"
GOLD = "#F3BA2F"
GREEN = "#16C784"
RED = "#EA3943"

st.set_page_config(page_title=f"{APP_NAME} {APP_VERSION}", page_icon="✦", layout="centered", initial_sidebar_state="collapsed")


def pct_class(value: float) -> str:
    return "positive" if value >= 0 else "negative"


def safe_width(value: float) -> int:
    return max(0, min(100, int(value)))


def sparkline_svg(values: Iterable[float], stroke: str = GOLD) -> str:
    points = [float(v) for v in values if isinstance(v, int | float) and math.isfinite(float(v))]
    if len(points) < 2:
        points = [1, 1.01, 1.0, 1.02, 1.015, 1.03]
    sample = points[-42:]
    low, high = min(sample), max(sample)
    spread = high - low or 1
    coords = []
    for index, value in enumerate(sample):
        x = index * (150 / (len(sample) - 1))
        y = 54 - ((value - low) / spread * 46) + 4
        coords.append(f"{x:.1f},{y:.1f}")
    fill_path = f"M {' L '.join(coords)} L 150,62 L 0,62 Z"
    gradient_id = f"goldFade{abs(hash(tuple(round(p, 4) for p in sample[-8:]))) % 100000}"
    return (
        "<svg class='sparkline' viewBox='0 0 150 64' preserveAspectRatio='none' aria-hidden='true'>"
        f"<defs><linearGradient id='{gradient_id}' x1='0' y1='0' x2='0' y2='1'><stop offset='0%' stop-color='{stroke}' stop-opacity='.45'/><stop offset='100%' stop-color='{stroke}' stop-opacity='0'/></linearGradient></defs>"
        f"<path d='{fill_path}' fill='url(#{gradient_id})'></path>"
        f"<polyline points='{' '.join(coords)}' fill='none' stroke='{stroke}' stroke-width='3.5' stroke-linecap='round' stroke-linejoin='round'></polyline>"
        "</svg>"
    )


def coin_logo(coin: MarketCoin | None, symbol: str) -> str:
    if coin and coin.image:
        return f"<img class='coin-logo' src='{html.escape(coin.image)}' alt='{html.escape(symbol)} logo'>"
    return f"<div class='coin-fallback'>{html.escape(symbol[:1] or '✦')}</div>"


def score_badge(score: int) -> str:
    label = "Prime" if score >= 75 else "Strong" if score >= 60 else "Neutral" if score >= 45 else "Risk"
    return f"<span class='score-badge'><b>{score}</b><small>{label}</small></span>"


def risk_label(coin: MarketCoin) -> tuple[str, str]:
    daily_range = ((coin.high_24h - coin.low_24h) / coin.current_price) * 100 if coin.current_price else 0
    if daily_range > 18 or coin.price_change_24h_pct < -12:
        return "High Risk", "risk-high"
    if daily_range > 8 or coin.price_change_7d_pct < -8:
        return "Medium Risk", "risk-med"
    return "Controlled", "risk-low"


def render_progress(label: str, value: int, detail: str = "") -> None:
    st.markdown(f"<div class='progress-row'><span>{html.escape(label)}</span><b>{value}%</b></div><div class='progress'><i style='width:{safe_width(value)}%'></i></div>{f'<p class=muted>{html.escape(detail)}</p>' if detail else ''}", unsafe_allow_html=True)


def render_market_card(coin: MarketCoin, owned_value: float = 0, favorite: bool = False) -> None:
    rec = recommendation_for(coin)
    risk, risk_class = risk_label(coin)
    rank = f"#{coin.market_cap_rank}" if coin.market_cap_rank else "—"
    opportunity = "Opportunity" if rec.opportunity_score >= 60 else "Watch" if rec.opportunity_score >= 45 else "Defensive"
    heart = "♥" if favorite else "♡"
    st.markdown(
        f"""
        <article class="coin-card float-in">
          <div class="coin-row">
            <div class="coin-title">{coin_logo(coin, coin.symbol)}<div><h3>{html.escape(coin.name)}</h3><p>{html.escape(coin.symbol)} · Rank {rank}</p></div></div>
            <div class="price-stack"><button class="fav" aria-label="favorite">{heart}</button><strong>{format_money(coin.current_price)}</strong><span class="{pct_class(coin.price_change_24h_pct)}">24h {format_pct(coin.price_change_24h_pct)}</span></div>
          </div>
          {sparkline_svg(coin.sparkline, GREEN if coin.price_change_7d_pct >= 0 else RED)}
          <div class="metric-grid"><span>7D <b class="{pct_class(coin.price_change_7d_pct)}">{format_pct(coin.price_change_7d_pct)}</b></span><span>Volume <b>{format_money(coin.total_volume)}</b></span><span>AI Score <b>{rec.opportunity_score}</b></span></div>
          <div class="badge-row"><em>{opportunity}</em><em class="{risk_class}">{risk}</em>{f'<em>Holding {format_money(owned_value)}</em>' if owned_value else ''}</div>
        </article>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
<style>
:root{--bg:#0B0E11;--card:#1A1D24;--gold:#F3BA2F;--text:#fff;--muted:#9AA4B2;--green:#16C784;--red:#EA3943;--line:rgba(255,255,255,.10);--glass:rgba(26,29,36,.72);}
.stApp{background:radial-gradient(circle at 12% -10%,rgba(243,186,47,.23),transparent 32%),radial-gradient(circle at 100% 0%,rgba(255,255,255,.07),transparent 27%),linear-gradient(180deg,#0B0E11 0%,#07090c 100%);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Inter",sans-serif;}
.block-container{max-width:430px!important;padding:1.1rem .95rem 6.9rem!important;overflow-x:hidden}#MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="stDecoration"],.stDeployButton{display:none!important}.stApp *{box-sizing:border-box}.topbar,.section-head,.coin-row,.coin-title,.metric-line,.progress-row,.setting-row{display:flex;align-items:center;justify-content:space-between;gap:.8rem}.topbar{position:sticky;top:.4rem;z-index:99;margin:-.15rem 0 .8rem;padding:.62rem .7rem;border:1px solid var(--line);border-radius:22px;background:rgba(11,14,17,.72);backdrop-filter:blur(22px);box-shadow:0 18px 50px rgba(0,0,0,.28)}.hello h1{font-size:1.42rem;letter-spacing:-.055em;margin:.1rem 0}.muted,.hello p,.coin-title p,.mini-stat span{color:var(--muted);font-size:.76rem;margin:.12rem 0}.icon-btn,.fav{width:44px;height:44px;border:1px solid var(--line);border-radius:16px;background:linear-gradient(145deg,rgba(255,255,255,.08),rgba(255,255,255,.02));color:#fff;display:grid;place-items:center;box-shadow:inset 0 1px 0 rgba(255,255,255,.08)}.portfolio-card,.coin-card,.glass-card,.ai-card{border-radius:22px;background:linear-gradient(145deg,rgba(255,255,255,.09),rgba(255,255,255,.03)),var(--glass);border:1px solid var(--line);box-shadow:0 22px 55px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.10);backdrop-filter:blur(20px);padding:1rem;margin:.85rem 0;overflow:hidden}.portfolio-card{background:radial-gradient(circle at 14% 0%,rgba(243,186,47,.28),transparent 45%),linear-gradient(145deg,#252833,#11141b)}.eyebrow{display:inline-flex;align-items:center;gap:.35rem;color:#161102;background:linear-gradient(135deg,var(--gold),#FFE29A);font-weight:900;font-size:.66rem;border-radius:999px;padding:.28rem .55rem}.value{font-size:2.15rem;font-weight:900;letter-spacing:-.075em;margin:.55rem 0 .25rem}.quick-grid,.metric-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.58rem}.mini-stat,.metric-grid span{background:rgba(0,0,0,.22);border:1px solid var(--line);border-radius:17px;padding:.72rem .62rem;min-width:0}.mini-stat b,.metric-grid b{display:block;font-size:.85rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.positive{color:var(--green)!important}.negative{color:var(--red)!important}.sparkline{width:100%;height:64px;margin:.7rem 0}.coin-card{transition:transform .22s ease,border-color .22s ease}.coin-card:hover{transform:translateY(-2px);border-color:rgba(243,186,47,.35)}.coin-logo,.coin-fallback{width:42px;height:42px;border-radius:50%;box-shadow:0 0 0 1px rgba(255,255,255,.12)}.coin-fallback{display:grid;place-items:center;background:linear-gradient(135deg,var(--gold),#8b681d);color:#111;font-weight:900}.coin-title{justify-content:flex-start}.coin-title h3{font-size:1rem;letter-spacing:-.04em;margin:0}.price-stack{text-align:right;display:flex;align-items:flex-end;flex-direction:column;gap:.15rem}.price-stack strong{font-size:.98rem}.price-stack span{font-size:.7rem}.fav{width:30px;height:30px;border-radius:11px;color:var(--gold)}.badge-row{display:flex;gap:.45rem;flex-wrap:wrap;margin-top:.7rem}.badge-row em{font-style:normal;font-weight:800;font-size:.68rem;padding:.32rem .52rem;border-radius:999px;border:1px solid rgba(243,186,47,.25);background:rgba(243,186,47,.12);color:#FFE29A}.badge-row .risk-high{border-color:rgba(234,57,67,.35);background:rgba(234,57,67,.13);color:#ff9aa1}.badge-row .risk-med{border-color:rgba(243,186,47,.35)}.badge-row .risk-low{border-color:rgba(22,199,132,.35);background:rgba(22,199,132,.13);color:#9ff0cc}.score-badge{min-width:62px;height:46px;border-radius:16px;display:flex;align-items:center;justify-content:center;gap:.1rem;flex-direction:column;background:linear-gradient(135deg,var(--gold),#74551a);color:#0B0E11;box-shadow:0 12px 35px rgba(243,186,47,.22)}.score-badge b{font-size:1.05rem}.score-badge small{font-size:.56rem;font-weight:900;text-transform:uppercase}.progress{height:9px;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden;margin:.35rem 0 .7rem}.progress i{display:block;height:100%;background:linear-gradient(90deg,#8A6419,var(--gold),#FFF2BF);border-radius:999px;animation:loadbar .8s ease}.progress-row span{font-size:.78rem;color:#DDE2EA}.progress-row b{font-size:.78rem;color:var(--gold)}.stButton>button,.stDownloadButton>button{border-radius:17px!important;min-height:46px!important;border:1px solid rgba(243,186,47,.35)!important;background:linear-gradient(135deg,rgba(243,186,47,.22),rgba(255,255,255,.06))!important;color:#fff!important;transition:transform .18s ease}.stButton>button:active{transform:scale(.98)}.stTextInput input,.stNumberInput input,.stTextArea textarea,.stSelectbox div[data-baseweb="select"]{border-radius:16px!important;background:rgba(255,255,255,.06)!important;border-color:var(--line)!important;color:#fff!important;min-height:46px}.stMultiSelect div[data-baseweb="select"]{border-radius:16px!important;background:rgba(255,255,255,.06)!important}.stExpander{border:1px solid var(--line)!important;border-radius:22px!important;background:rgba(26,29,36,.5)!important;overflow:hidden}.skeleton{height:82px;border-radius:22px;background:linear-gradient(90deg,rgba(255,255,255,.05),rgba(255,255,255,.12),rgba(255,255,255,.05));background-size:220% 100%;animation:shimmer 1.4s infinite}.settings-title{font-size:1.2rem;margin:.1rem 0;letter-spacing:-.04em}.setting-row{padding:.75rem 0;border-bottom:1px solid var(--line)}div[role="radiogroup"]{position:fixed;left:50%;bottom:.55rem;transform:translateX(-50%);z-index:1000;width:min(410px,calc(100vw - 18px));display:grid!important;grid-template-columns:repeat(5,1fr);gap:.25rem;background:rgba(11,14,17,.86);border:1px solid var(--line);backdrop-filter:blur(24px);border-radius:24px;padding:.35rem;box-shadow:0 20px 50px rgba(0,0,0,.45)}div[role="radiogroup"] label{justify-content:center;border-radius:18px;padding:.38rem .1rem!important;margin:0!important;min-height:52px;background:transparent}div[role="radiogroup"] label:has(input:checked){background:linear-gradient(135deg,rgba(243,186,47,.25),rgba(255,255,255,.08))}div[role="radiogroup"] p{font-size:0!important}div[role="radiogroup"] p::first-letter{font-size:1.25rem!important}@keyframes shimmer{to{background-position:-220% 0}}@keyframes loadbar{from{width:0}}.float-in{animation:floatIn .5s cubic-bezier(.2,.8,.2,1) both}@keyframes floatIn{from{opacity:0;transform:translateY(14px) scale(.98)}to{opacity:1;transform:none}}@media(max-width:390px){.block-container{padding-left:.75rem!important;padding-right:.75rem!important}.value{font-size:1.9rem}.quick-grid,.metric-grid{gap:.45rem}.mini-stat,.metric-grid span{padding:.62rem .5rem}}
</style>
""",
    unsafe_allow_html=True,
)

client = CoinGeckoClient()
default_state = {"portfolio": empty_portfolio(), "watchlist": ["bitcoin", "ethereum", "solana"], "screen": "⌂", "currency": "USD", "theme": "Premium Dark", "refresh_interval": "90 seconds"}
for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

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
def load_markets(ids: tuple[str, ...], currency: str) -> pd.DataFrame:
    return markets_to_frame(client.fetch_markets(ids, currency=currency.lower()))

try:
    if refresh:
        load_markets.clear()
    market_df = load_markets(tuple(coin_ids), st.session_state.currency)
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
daily_pnl = sum(float(row["value"]) * (float(market_lookup[row["coin_id"]].price_change_24h_pct) / 100) for _, row in portfolio.iterrows() if row["coin_id"] in market_lookup)
daily_pnl_pct = (daily_pnl / max(total_value - daily_pnl, 1) * 100) if total_value else 0.0
alerts = triggered_alerts(st.session_state.portfolio, market_objects)
fav_ids = set(st.session_state.portfolio.loc[st.session_state.portfolio["favorite"], "coin_id"]) if not st.session_state.portfolio.empty else set()
best_row = portfolio.sort_values("pnl_pct", ascending=False).head(1) if not portfolio.empty else pd.DataFrame()
worst_row = portfolio.sort_values("pnl_pct", ascending=True).head(1) if not portfolio.empty else pd.DataFrame()

st.markdown("<div class='topbar'><div class='hello'><p>Good Morning, Mouad 👋</p><h1>Trader AI</h1></div><div class='top-actions'><span class='icon-btn'>↻</span><span class='icon-btn'>⌁</span></div></div>", unsafe_allow_html=True)
screen = st.radio("Navigation", ["⌂", "◎", "♡", "✦", "⚙"], horizontal=True, label_visibility="collapsed", key="screen")

if screen == "⌂":
    st.markdown(f"""
    <section class='portfolio-card float-in'><span class='eyebrow'>PORTFOLIO VALUE</span><div class='value'>{format_money(total_value)}</div><div class='quick-grid'><div class='mini-stat'><span>Daily P&L</span><b class='{pct_class(daily_pnl)}'>{format_money(daily_pnl)}<br>{format_pct(daily_pnl_pct)}</b></div><div class='mini-stat'><span>Total Return</span><b class='{pct_class(total_pnl_pct)}'>{format_money(total_pnl)}<br>{format_pct(total_pnl_pct)}</b></div><div class='mini-stat'><span>Assets</span><b>{len(portfolio)}</b></div></div>{sparkline_svg([sum((market_lookup.get(str(r['coin_id'])).sparkline[i] if market_lookup.get(str(r['coin_id'])) and len(market_lookup[str(r['coin_id'])].sparkline)>i else 0)*float(r['quantity']) for _, r in portfolio.iterrows()) for i in range(0, 42)] if not portfolio.empty else [])}<div class='metric-line'><span class='muted'>Allocation leader</span><b>{portfolio.iloc[0]['symbol'] + ' ' + format_pct(float(portfolio.iloc[0]['allocation_pct'])) if not portfolio.empty else '—'}</b></div><div class='metric-line'><span class='muted'>Top performer</span><b class='positive'>{best_row.iloc[0]['symbol'] + ' ' + format_pct(float(best_row.iloc[0]['pnl_pct'])) if not best_row.empty and not pd.isna(best_row.iloc[0]['pnl_pct']) else '—'}</b></div><div class='metric-line'><span class='muted'>Worst performer</span><b class='negative'>{worst_row.iloc[0]['symbol'] + ' ' + format_pct(float(worst_row.iloc[0]['pnl_pct'])) if not worst_row.empty and not pd.isna(worst_row.iloc[0]['pnl_pct']) else '—'}</b></div></section>
    """, unsafe_allow_html=True)
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

elif screen == "◎":
    st.markdown("<div class='section-head'><h2>Markets</h2><span class='muted'>Premium cards</span></div>", unsafe_allow_html=True)
    sort_by = st.selectbox("Sort", ["Market rank", "AI score", "24h gain", "7d gain", "Volume"])
    coins = market_objects[:]
    if sort_by == "AI score": coins.sort(key=lambda c: recommendation_for(c).opportunity_score, reverse=True)
    elif sort_by == "24h gain": coins.sort(key=lambda c: c.price_change_24h_pct, reverse=True)
    elif sort_by == "7d gain": coins.sort(key=lambda c: c.price_change_7d_pct, reverse=True)
    elif sort_by == "Volume": coins.sort(key=lambda c: c.total_volume, reverse=True)
    for coin in coins:
        render_market_card(coin, favorite=coin.coin_id in fav_ids or coin.coin_id in st.session_state.watchlist)

elif screen == "♡":
    st.markdown("<div class='section-head'><h2>Watchlist</h2><span class='muted'>Swipe-style cards</span></div>", unsafe_allow_html=True)
    query = st.text_input("Search", placeholder="Search coin or ticker")
    picks = st.multiselect("Add/remove favorites", options=market_ids, default=[x for x in st.session_state.watchlist if x in market_ids], format_func=lambda cid: f"{market_lookup[cid].name} ({market_lookup[cid].symbol})")
    st.session_state.watchlist = picks
    filter_mode = st.selectbox("Filter", ["All", "Gainers", "Decliners", "High AI score"])
    sort_mode = st.selectbox("Sort watchlist", ["AI score", "Rank", "24h", "7d"])
    watch_ids = list(dict.fromkeys([*picks, *fav_ids]))
    watch_coins = [market_lookup[cid] for cid in watch_ids if cid in market_lookup and (not query or query.lower() in market_lookup[cid].name.lower() or query.lower() in market_lookup[cid].symbol.lower())]
    if filter_mode == "Gainers": watch_coins = [c for c in watch_coins if c.price_change_24h_pct >= 0]
    elif filter_mode == "Decliners": watch_coins = [c for c in watch_coins if c.price_change_24h_pct < 0]
    elif filter_mode == "High AI score": watch_coins = [c for c in watch_coins if recommendation_for(c).opportunity_score >= 60]
    if sort_mode == "AI score": watch_coins.sort(key=lambda c: recommendation_for(c).opportunity_score, reverse=True)
    elif sort_mode == "Rank": watch_coins.sort(key=lambda c: c.market_cap_rank or 9999)
    elif sort_mode == "24h": watch_coins.sort(key=lambda c: c.price_change_24h_pct, reverse=True)
    else: watch_coins.sort(key=lambda c: c.price_change_7d_pct, reverse=True)
    for coin in watch_coins:
        render_market_card(coin, favorite=True)

elif screen == "✦":
    st.markdown("<div class='section-head'><h2>AI Intelligence</h2><span class='muted'>Educational rubric</span></div>", unsafe_allow_html=True)
    selected = st.selectbox("Analyze asset", options=market_ids, format_func=lambda cid: f"{market_lookup[cid].name} ({market_lookup[cid].symbol})")
    coin = market_lookup[selected]
    rec = recommendation_for(coin)
    trend = safe_width(50 + coin.price_change_7d_pct)
    momentum = safe_width(50 + coin.price_change_24h_pct * 2)
    risk = safe_width(100 - (20 if risk_label(coin)[0] == "Controlled" else 48 if risk_label(coin)[0] == "Medium Risk" else 72))
    confidence = safe_width((rec.opportunity_score + trend + risk) / 3)
    st.markdown(f"<section class='ai-card float-in'><div class='coin-row'><div class='coin-title'>{coin_logo(coin, coin.symbol)}<div><h3>{html.escape(coin.name)} AI</h3><p>{html.escape(coin.symbol)} · original scoring</p></div></div>{score_badge(rec.opportunity_score)}</div><p class='muted'>Momentum is improving while volatility remains controlled.</p></section>", unsafe_allow_html=True)
    render_progress("Opportunity score", rec.opportunity_score, rec.rationale)
    render_progress("Trend score", trend)
    render_progress("Momentum", momentum)
    render_progress("Risk control", risk)
    render_progress("Confidence", confidence, "Educational analysis only — not financial advice.")

else:
    st.markdown("<section class='glass-card'><h2 class='settings-title'>Settings</h2><p class='muted'>Tune the mobile experience. Trader AI uses public CoinGecko data only and cannot trade, custody assets, or connect to exchange APIs.</p></section>", unsafe_allow_html=True)
    st.session_state.theme = st.selectbox("Theme", ["Premium Dark"], index=0)
    st.session_state.currency = st.selectbox("Currency", ["USD", "EUR", "GBP"], index=["USD", "EUR", "GBP"].index(st.session_state.currency))
    st.session_state.refresh_interval = st.selectbox("Refresh interval", ["60 seconds", "90 seconds", "5 minutes"], index=["60 seconds", "90 seconds", "5 minutes"].index(st.session_state.refresh_interval))
    st.markdown(f"<section class='glass-card'><div class='setting-row'><span>About</span><b>{APP_NAME} v{APP_VERSION}</b></div><div class='setting-row'><span>Data source</span><b>CoinGecko</b></div><p class='muted'><b>Educational disclaimer:</b> Trader AI is for market education and research. It does not provide financial advice and does not execute trades.</p></section>", unsafe_allow_html=True)
