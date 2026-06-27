from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import enrich_portfolio, format_money, format_pct, recommendation_for
from coingecko import DEFAULT_COINS, CoinGeckoClient, MarketCoin, markets_to_frame
from sample_data import default_portfolio

APP_NAME = "Trader AI"
APP_VERSION = "0.1"


st.set_page_config(page_title=f"{APP_NAME} {APP_VERSION}", page_icon="🟢", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1200px;}
    [data-testid="stMetricValue"] {font-size: clamp(1.35rem, 4vw, 2.2rem);}
    .hero {border: 1px solid rgba(34,197,94,.25); background: linear-gradient(135deg, rgba(34,197,94,.16), rgba(15,23,42,.95)); border-radius: 24px; padding: 1.4rem; margin-bottom: 1rem;}
    .hero h1 {margin: 0 0 .25rem 0; font-size: clamp(2rem, 8vw, 4rem);}
    .hero p {color: #cbd5e1; margin-bottom: 0;}
    .pill {display: inline-block; padding: .25rem .65rem; border-radius: 999px; background: rgba(34,197,94,.16); color: #86efac; font-size: .85rem; margin-bottom: .75rem;}
    @media (max-width: 640px) {.block-container {padding-left: .8rem; padding-right: .8rem;} div[data-testid="stHorizontalBlock"] {gap: .4rem;}}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <section class="hero">
      <span class="pill">{APP_NAME} · v{APP_VERSION} · CoinGecko only</span>
      <h1>Crypto portfolio command center</h1>
      <p>Track a manual portfolio, monitor live public market data, and rank opportunities without API keys or exchange integrations.</p>
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
    st.caption("No Binance API · No API keys · Educational analysis only")

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
    if refresh:
        load_markets.clear()
    market_df = load_markets(tuple(coin_ids))
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

if market_df.empty:
    st.warning("Add at least one valid CoinGecko coin ID to begin.")
    st.stop()

# Rehydrate market rows after Streamlit caching so analytics can work with typed objects.
market_objects = [MarketCoin(**row.to_dict()) for _, row in market_df.iterrows()]
market_ids = [coin.coin_id for coin in market_objects]

if "portfolio" not in st.session_state:
    st.session_state.portfolio = default_portfolio()

st.subheader("Manual portfolio")
st.caption("Edit quantities and average costs locally in the table below. Nothing is sent to an exchange.")
portfolio_input = st.data_editor(
    st.session_state.portfolio,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "coin_id": st.column_config.SelectboxColumn("CoinGecko ID", options=market_ids, required=True),
        "quantity": st.column_config.NumberColumn("Quantity", min_value=0.0, step=0.0001, format="%.8f"),
        "avg_cost": st.column_config.NumberColumn("Average cost (USD)", min_value=0.0, step=1.0, format="$%.4f"),
    },
    hide_index=True,
)
st.session_state.portfolio = portfolio_input

portfolio = enrich_portfolio(portfolio_input, market_objects)
total_value = float(portfolio["value"].sum()) if not portfolio.empty else 0.0
total_cost = float(portfolio["cost_basis"].sum()) if not portfolio.empty else 0.0
total_pnl = total_value - total_cost
total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0.0
best_market = max(market_objects, key=lambda coin: recommendation_for(coin).opportunity_score)
best_rec = recommendation_for(best_market)

metric_cols = st.columns(4)
metric_cols[0].metric("Portfolio value", format_money(total_value))
metric_cols[1].metric("Unrealized P&L", format_money(total_pnl), format_pct(total_pnl_pct))
metric_cols[2].metric("Tracked assets", len(market_objects))
metric_cols[3].metric("Top opportunity", f"{best_rec.symbol} · {best_rec.opportunity_score}/100")

left, right = st.columns([1.25, 1], gap="large")
with left:
    st.subheader("Holdings, value, P&L, allocation")
    display_portfolio = portfolio.copy()
    if not display_portfolio.empty:
        for column in ["avg_cost", "current_price", "value", "cost_basis", "pnl"]:
            display_portfolio[column] = display_portfolio[column].map(lambda value: f"${value:,.2f}")
        display_portfolio["pnl_pct"] = display_portfolio["pnl_pct"].map(lambda value: "—" if pd.isna(value) else f"{value:+.2f}%")
        display_portfolio["allocation_pct"] = display_portfolio["allocation_pct"].map(lambda value: f"{value:.2f}%")
    st.dataframe(display_portfolio, use_container_width=True, hide_index=True)

with right:
    st.subheader("Allocation")
    if not portfolio.empty and total_value > 0:
        st.bar_chart(portfolio.set_index("symbol")[["allocation_pct"]], use_container_width=True)
    else:
        st.info("Add holdings to see allocation.")

st.divider()
st.subheader("Opportunity score & recommendation engine")
recommendations = [recommendation_for(coin) for coin in market_objects]
rec_df = pd.DataFrame([rec.__dict__ for rec in recommendations]).sort_values("opportunity_score", ascending=False)
st.dataframe(
    rec_df.rename(
        columns={
            "coin_id": "CoinGecko ID",
            "symbol": "Symbol",
            "name": "Name",
            "opportunity_score": "Opportunity score",
            "action": "Recommendation",
            "rationale": "Rationale",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Market dashboard")
market_display = market_df[["name", "symbol", "current_price", "market_cap_rank", "price_change_24h_pct", "price_change_7d_pct", "price_change_30d_pct", "total_volume"]].copy()
market_display.columns = ["Name", "Symbol", "Price", "Rank", "24h", "7d", "30d", "Volume"]
st.dataframe(market_display, use_container_width=True, hide_index=True)

st.caption("Disclaimer: Trader AI is not financial advice. It is a research dashboard built only on public CoinGecko data.")
