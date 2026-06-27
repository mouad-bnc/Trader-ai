from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import enrich_portfolio, format_money, format_pct, portfolio_performance_frame, recommendation_for, triggered_alerts
from coingecko import DEFAULT_COINS, CoinGeckoClient, MarketCoin, markets_to_frame
from portfolio_io import empty_portfolio, normalize_portfolio, parse_binance_spot_csv

APP_NAME = "Trader AI"
APP_VERSION = "1.0"

st.set_page_config(page_title=f"{APP_NAME} {APP_VERSION}", page_icon="₿", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.stApp {background: radial-gradient(circle at top left, #123524 0, #080b14 34%, #05070d 100%); color:#e5eefb;}
.block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 1220px;}
[data-testid="stSidebar"] {background: rgba(2,6,23,.92); border-right: 1px solid rgba(148,163,184,.15);}
[data-testid="stMetric"] {background: rgba(15,23,42,.72); border: 1px solid rgba(148,163,184,.16); border-radius: 20px; padding: 1rem; box-shadow: 0 18px 50px rgba(0,0,0,.25);}
[data-testid="stMetricValue"] {font-size: clamp(1.25rem, 4vw, 2rem);}
.hero {border: 1px solid rgba(45,212,191,.28); background: linear-gradient(135deg, rgba(20,184,166,.20), rgba(15,23,42,.84)); border-radius: 28px; padding: clamp(1rem, 5vw, 2rem); margin-bottom: 1rem; box-shadow: 0 25px 80px rgba(0,0,0,.28);}
.hero h1 {margin: .15rem 0 .45rem; font-size: clamp(2rem, 9vw, 4.6rem); letter-spacing:-.06em;}
.hero p {color: #cbd5e1; margin: 0; max-width: 780px;}
.pill {display:inline-flex; gap:.45rem; align-items:center; padding:.32rem .72rem; border-radius:999px; background:rgba(45,212,191,.14); color:#99f6e4; border:1px solid rgba(45,212,191,.25); font-size:.85rem;}
.card {background: rgba(15,23,42,.70); border:1px solid rgba(148,163,184,.14); border-radius:22px; padding:1rem; margin:.5rem 0 1rem;}
.disclaimer {color:#fef3c7; background:rgba(180,83,9,.16); border:1px solid rgba(251,191,36,.28); border-radius:16px; padding:.85rem;}
@media (max-width: 640px) {.block-container {padding-left:.65rem; padding-right:.65rem;} div[data-testid="stHorizontalBlock"] {gap:.35rem;} .hero {border-radius:20px;}}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<section class="hero">
  <span class="pill">{APP_NAME} · v{APP_VERSION} · educational only</span>
  <h1>Professional crypto portfolio platform</h1>
  <p>Edit real holdings, import Binance Spot CSV files, monitor CoinGecko market data, track alerts, and rank opportunities with transparent AI-style scoring. No trading, custody, API keys, or financial advice.</p>
</section>
""", unsafe_allow_html=True)

client = CoinGeckoClient()
if "portfolio" not in st.session_state:
    st.session_state.portfolio = empty_portfolio()
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["bitcoin", "ethereum", "solana"]

with st.sidebar:
    st.header("Portfolio setup")
    uploaded = st.file_uploader("Import Binance Spot CSV", type=["csv"], help="Supports Spot balance snapshots and trade exports.")
    if uploaded is not None:
        try:
            imported = parse_binance_spot_csv(uploaded)
            if st.button("Use imported portfolio", type="primary", use_container_width=True):
                st.session_state.portfolio = imported
                st.success(f"Imported {len(imported)} assets.")
        except Exception as exc:
            st.error(str(exc))
    st.divider()
    st.header("Market universe")
    base_ids = set(st.session_state.portfolio.get("coin_id", pd.Series(dtype=str)).dropna().astype(str))
    default_ids = ", ".join(dict.fromkeys([*DEFAULT_COINS, *st.session_state.watchlist, *base_ids]))
    coin_ids_text = st.text_area("CoinGecko IDs", value=default_ids, height=130)
    include_trending = st.toggle("Include trending", value=True)
    refresh = st.button("Refresh market data", use_container_width=True)
    st.caption("Public CoinGecko data · local browser session state")

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
market_ids = [coin.coin_id for coin in market_objects]

st.subheader("Editable portfolio")
st.caption("Enter your own holdings. Average cost and alert fields are optional; data stays in this Streamlit session unless you export it.")
portfolio_input = st.data_editor(
    normalize_portfolio(st.session_state.portfolio), num_rows="dynamic", use_container_width=True, hide_index=True,
    column_config={
        "coin_id": st.column_config.SelectboxColumn("CoinGecko ID", options=market_ids, required=True),
        "symbol": st.column_config.TextColumn("Symbol"),
        "quantity": st.column_config.NumberColumn("Quantity", min_value=0.0, step=0.0001, format="%.8f"),
        "avg_cost": st.column_config.NumberColumn("Avg cost", min_value=0.0, step=1.0, format="$%.4f"),
        "alert_below": st.column_config.NumberColumn("Alert below", min_value=0.0, step=1.0, format="$%.4f"),
        "alert_above": st.column_config.NumberColumn("Alert above", min_value=0.0, step=1.0, format="$%.4f"),
        "favorite": st.column_config.CheckboxColumn("★"),
        "notes": st.column_config.TextColumn("Notes"),
    },
)
st.session_state.portfolio = normalize_portfolio(portfolio_input)
portfolio = enrich_portfolio(st.session_state.portfolio, market_objects)

total_value = float(portfolio["value"].sum()) if not portfolio.empty else 0.0
total_cost = float(portfolio["cost_basis"].sum()) if not portfolio.empty else 0.0
total_pnl = total_value - total_cost
total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0.0
best_market = max(market_objects, key=lambda coin: recommendation_for(coin).opportunity_score)
best_rec = recommendation_for(best_market)
alerts = triggered_alerts(st.session_state.portfolio, market_objects)

cols = st.columns(4)
cols[0].metric("Portfolio value", format_money(total_value))
cols[1].metric("Unrealized P&L", format_money(total_pnl), format_pct(total_pnl_pct))
cols[2].metric("Active alerts", len(alerts))
cols[3].metric("Top AI score", f"{best_rec.symbol} · {best_rec.opportunity_score}/100")

if not alerts.empty:
    st.warning("Price alerts triggered")
    st.dataframe(alerts, use_container_width=True, hide_index=True)

tab_portfolio, tab_charts, tab_watch, tab_ai, tab_market = st.tabs(["Holdings", "Charts", "Watchlist", "AI scoring", "Markets"])
with tab_portfolio:
    st.download_button("Export portfolio CSV", st.session_state.portfolio.to_csv(index=False), "trader_ai_portfolio.csv", "text/csv")
    display = portfolio.copy()
    if not display.empty:
        for column in ["avg_cost", "current_price", "value", "cost_basis", "pnl"]:
            display[column] = display[column].map(lambda value: f"${value:,.2f}")
        display["pnl_pct"] = display["pnl_pct"].map(lambda value: "—" if pd.isna(value) else f"{value:+.2f}%")
        display["allocation_pct"] = display["allocation_pct"].map(lambda value: f"{value:.2f}%")
    st.dataframe(display, use_container_width=True, hide_index=True)
with tab_charts:
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("<div class='card'>Estimated 7-day portfolio performance from CoinGecko sparklines</div>", unsafe_allow_html=True)
        perf = portfolio_performance_frame(st.session_state.portfolio, market_objects)
        if perf.empty or perf["estimated_value"].sum() == 0:
            st.info("Add holdings with supported CoinGecko IDs to see performance.")
        else:
            st.line_chart(perf, x="point", y="estimated_value", use_container_width=True)
    with right:
        st.markdown("<div class='card'>Allocation by asset</div>", unsafe_allow_html=True)
        if not portfolio.empty and total_value > 0:
            st.bar_chart(portfolio.set_index("symbol")[["allocation_pct"]], use_container_width=True)
        else:
            st.info("Add holdings to see allocation.")
with tab_watch:
    picks = st.multiselect("Watchlist / favorites", options=market_ids, default=[x for x in st.session_state.watchlist if x in market_ids])
    st.session_state.watchlist = picks
    watch = market_df[market_df["coin_id"].isin(picks)].copy()
    fav_ids = set(st.session_state.portfolio.loc[st.session_state.portfolio["favorite"], "coin_id"]) if not st.session_state.portfolio.empty else set()
    favorites = market_df[market_df["coin_id"].isin(fav_ids)].copy()
    st.write("Favorites from portfolio")
    st.dataframe(favorites[["name", "symbol", "current_price", "price_change_24h_pct", "price_change_7d_pct"]], use_container_width=True, hide_index=True)
    st.write("Watchlist")
    st.dataframe(watch[["name", "symbol", "current_price", "market_cap_rank", "price_change_24h_pct", "price_change_7d_pct"]], use_container_width=True, hide_index=True)
with tab_ai:
    recommendations = [recommendation_for(coin) for coin in market_objects]
    rec_df = pd.DataFrame([rec.__dict__ for rec in recommendations]).sort_values("opportunity_score", ascending=False)
    st.dataframe(rec_df.rename(columns={"coin_id":"CoinGecko ID","symbol":"Symbol","name":"Name","opportunity_score":"AI opportunity score","action":"Educational stance","rationale":"Rationale"}), use_container_width=True, hide_index=True)
    st.markdown("<div class='disclaimer'>AI scoring is a deterministic educational rubric using public momentum, liquidity, rank, volatility, and drawdown fields. It is not a buy/sell signal.</div>", unsafe_allow_html=True)
with tab_market:
    market_display = market_df[["name", "symbol", "current_price", "market_cap_rank", "price_change_24h_pct", "price_change_7d_pct", "price_change_30d_pct", "total_volume"]].copy()
    market_display.columns = ["Name", "Symbol", "Price", "Rank", "24h", "7d", "30d", "Volume"]
    st.dataframe(market_display, use_container_width=True, hide_index=True)

st.caption("Disclaimer: Trader AI is educational software only. It does not provide financial, investment, tax, or legal advice and cannot place trades.")
