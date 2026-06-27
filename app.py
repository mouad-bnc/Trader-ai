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
    label = "Excellent" if score >= 75 else "Fort" if score >= 60 else "Neutre" if score >= 45 else "Risque"
    return f"<span class='score-badge'><b>{score}</b><small>{label}</small></span>"


def risk_label(coin: MarketCoin) -> tuple[str, str]:
    daily_range = ((coin.high_24h - coin.low_24h) / coin.current_price) * 100 if coin.current_price else 0
    if daily_range > 18 or coin.price_change_24h_pct < -12:
        return "Élevé", "risk-high"
    if daily_range > 8 or coin.price_change_7d_pct < -8:
        return "Moyen", "risk-med"
    return "Faible", "risk-low"


def ai_badge(score: int) -> str:
    if score >= 78:
        return "Achat fort"
    if score >= 62:
        return "Achat"
    if score >= 45:
        return "Conserver"
    if score >= 32:
        return "Réduire"
    return "Éviter"


def confidence_for(coin: MarketCoin) -> int:
    rec = recommendation_for(coin)
    volatility_penalty = min(30, volatility_pct(coin) * 1.5)
    return safe_width(58 + (rec.opportunity_score - 50) * .45 - volatility_penalty + min(14, abs(coin.price_change_7d_pct)))


def volatility_pct(coin: MarketCoin) -> float:
    return ((coin.high_24h - coin.low_24h) / coin.current_price * 100) if coin.current_price else 0


def one_sentence_summary(article: dict[str, object]) -> str:
    text = str(article.get("description") or article.get("summary") or article.get("title") or "Dernière actualité du marché crypto.")
    first = text.replace("\n", " ").split(". ")[0].strip()
    return (first[:137] + "…") if len(first) > 140 else first


def render_progress(label: str, value: int, detail: str = "") -> None:
    st.markdown(f"<div class='progress-row'><span>{html.escape(label)}</span><b>{value}%</b></div><div class='progress'><i style='width:{safe_width(value)}%'></i></div>{f'<p class=muted>{html.escape(detail)}</p>' if detail else ''}", unsafe_allow_html=True)


def render_market_card(coin: MarketCoin, owned_value: float = 0, favorite: bool = False) -> None:
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
            <div class="price-stack"><button class="fav" aria-label="favorite">{heart}</button><strong>{format_money(coin.current_price)}</strong><span class="{pct_class(coin.price_change_24h_pct)}">{trend_arrow} 24h {format_pct(coin.price_change_24h_pct)}</span></div>
          </div>
          {sparkline_svg(coin.sparkline, GREEN if coin.price_change_7d_pct >= 0 else RED)}
          <div class="metric-grid"><span>IA <b>{ai_badge(rec.opportunity_score)}</b></span><span>Risque <b class="{risk_class}">{risk}</b></span><span>Confiance <b>{confidence}%</b></span></div>
          <div class="volatility"><i style="width:{safe_width(vol * 4)}%"></i></div>
          <div class="badge-row"><em>{trend_arrow} Tendance</em><em>Volatilité {vol:.1f}%</em>{f'<em>Position {format_money(owned_value)}</em>' if owned_value else ''}</div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_holding_card(row: pd.Series, coin: MarketCoin | None) -> None:
    pnl = float(row.get("pnl") or 0)
    daily = coin.price_change_24h_pct if coin else 0
    st.markdown(f"""<article class='coin-card holding-card'>
      <div class='coin-row'><div class='coin-title'>{coin_logo(coin, str(row['symbol']))}<div><h3>{html.escape(str(row['name']))}</h3><p>{float(row['quantity']):,.8f} {html.escape(str(row['symbol']))}</p></div></div><div class='price-stack'><strong>{format_money(float(row['value']))}</strong><span class='{pct_class(pnl)}'>{format_money(pnl)} · {format_pct(float(row['pnl_pct'])) if not pd.isna(row['pnl_pct']) else '—'}</span></div></div>
      {sparkline_svg(coin.sparkline if coin else [], GREEN if daily >= 0 else RED)}
      <div class='metric-grid'><span>Prix moyen <b>{format_money(float(row['avg_cost']))}</b></span><span>Journalier <b class='{pct_class(daily)}'>{format_pct(daily)}</b></span><span>Allocation <b>{format_pct(float(row['allocation_pct']))}</b></span></div>
    </article>""", unsafe_allow_html=True)


st.markdown(
    """
<style>
:root{--bg:#0B0E11;--card:#1A1D24;--gold:#F3BA2F;--text:#fff;--muted:#9AA4B2;--green:#16C784;--red:#EA3943;--line:rgba(255,255,255,.10);--glass:rgba(26,29,36,.72);}
.stApp{background:radial-gradient(circle at 12% -10%,rgba(243,186,47,.23),transparent 32%),radial-gradient(circle at 100% 0%,rgba(255,255,255,.07),transparent 27%),linear-gradient(180deg,#0B0E11 0%,#07090c 100%);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Inter",sans-serif;}
.block-container{max-width:430px!important;padding:1.1rem .95rem 6.9rem!important;overflow-x:hidden}#MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="stDecoration"],.stDeployButton{display:none!important}.stApp *{box-sizing:border-box}.topbar,.section-head,.coin-row,.coin-title,.metric-line,.progress-row,.setting-row{display:flex;align-items:center;justify-content:space-between;gap:.8rem}.topbar{position:sticky;top:.4rem;z-index:99;margin:-.15rem 0 .8rem;padding:.62rem .7rem;border:1px solid var(--line);border-radius:22px;background:rgba(11,14,17,.72);backdrop-filter:blur(22px);box-shadow:0 18px 50px rgba(0,0,0,.28)}.hello h1{font-size:1.42rem;letter-spacing:-.055em;margin:.1rem 0}.muted,.hello p,.coin-title p,.mini-stat span{color:var(--muted);font-size:.76rem;margin:.12rem 0}.icon-btn,.fav{width:44px;height:44px;border:1px solid var(--line);border-radius:16px;background:linear-gradient(145deg,rgba(255,255,255,.08),rgba(255,255,255,.02));color:#fff;display:grid;place-items:center;box-shadow:inset 0 1px 0 rgba(255,255,255,.08)}.portfolio-card,.coin-card,.glass-card,.ai-card{border-radius:22px;background:linear-gradient(145deg,rgba(255,255,255,.09),rgba(255,255,255,.03)),var(--glass);border:1px solid var(--line);box-shadow:0 22px 55px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.10);backdrop-filter:blur(20px);padding:1rem;margin:.85rem 0;overflow:hidden}.portfolio-card{background:radial-gradient(circle at 14% 0%,rgba(243,186,47,.28),transparent 45%),linear-gradient(145deg,#252833,#11141b)}.eyebrow{display:inline-flex;align-items:center;gap:.35rem;color:#161102;background:linear-gradient(135deg,var(--gold),#FFE29A);font-weight:900;font-size:.66rem;border-radius:999px;padding:.28rem .55rem}.value{font-size:2.15rem;font-weight:900;letter-spacing:-.075em;margin:.55rem 0 .25rem}.quick-grid,.metric-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.58rem}.allocation-list{display:grid;gap:.5rem;margin-top:.8rem}.allocation-pill{display:grid;grid-template-columns:52px 1fr 48px;gap:.55rem;align-items:center}.allocation-bar{height:8px;background:rgba(255,255,255,.08);border-radius:99px;overflow:hidden}.allocation-bar i,.volatility i{display:block;height:100%;background:linear-gradient(90deg,#8A6419,var(--gold),#FFF2BF);border-radius:99px}.volatility{height:7px;background:rgba(255,255,255,.07);border-radius:99px;margin:.2rem 0 .55rem}.chart-large{height:230px}.news-card h3{font-size:1rem;line-height:1.18;margin:.2rem 0}.assistant-grid{display:grid;gap:.75rem}.assistant-card{border-radius:20px;padding:.9rem;background:rgba(255,255,255,.055);border:1px solid var(--line)}.mini-stat,.metric-grid span{background:rgba(0,0,0,.22);border:1px solid var(--line);border-radius:17px;padding:.72rem .62rem;min-width:0}.mini-stat b,.metric-grid b{display:block;font-size:.85rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.positive,.risk-low{color:var(--green)!important}.negative,.risk-high{color:var(--red)!important}.risk-med{color:var(--gold)!important}.sparkline{width:100%;height:64px;margin:.7rem 0}.coin-card{transition:transform .22s ease,border-color .22s ease}.coin-card:hover{transform:translateY(-2px);border-color:rgba(243,186,47,.35)}.coin-logo,.coin-fallback{width:42px;height:42px;border-radius:50%;box-shadow:0 0 0 1px rgba(255,255,255,.12)}.coin-fallback{display:grid;place-items:center;background:linear-gradient(135deg,var(--gold),#8b681d);color:#111;font-weight:900}.coin-title{justify-content:flex-start}.coin-title h3{font-size:1rem;letter-spacing:-.04em;margin:0}.price-stack{text-align:right;display:flex;align-items:flex-end;flex-direction:column;gap:.15rem}.price-stack strong{font-size:.98rem}.price-stack span{font-size:.7rem}.fav{width:30px;height:30px;border-radius:11px;color:var(--gold)}.badge-row{display:flex;gap:.45rem;flex-wrap:wrap;margin-top:.7rem}.badge-row em{font-style:normal;font-weight:800;font-size:.68rem;padding:.32rem .52rem;border-radius:999px;border:1px solid rgba(243,186,47,.25);background:rgba(243,186,47,.12);color:#FFE29A}.badge-row .risk-high{border-color:rgba(234,57,67,.35);background:rgba(234,57,67,.13);color:#ff9aa1}.badge-row .risk-med{border-color:rgba(243,186,47,.35)}.badge-row .risk-low{border-color:rgba(22,199,132,.35);background:rgba(22,199,132,.13);color:#9ff0cc}.score-badge{min-width:62px;height:46px;border-radius:16px;display:flex;align-items:center;justify-content:center;gap:.1rem;flex-direction:column;background:linear-gradient(135deg,var(--gold),#74551a);color:#0B0E11;box-shadow:0 12px 35px rgba(243,186,47,.22)}.score-badge b{font-size:1.05rem}.score-badge small{font-size:.56rem;font-weight:900;text-transform:uppercase}.progress{height:9px;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden;margin:.35rem 0 .7rem}.progress i{display:block;height:100%;background:linear-gradient(90deg,#8A6419,var(--gold),#FFF2BF);border-radius:999px;animation:loadbar .8s ease}.progress-row span{font-size:.78rem;color:#DDE2EA}.progress-row b{font-size:.78rem;color:var(--gold)}.stButton>button,.stDownloadButton>button{border-radius:17px!important;min-height:46px!important;border:1px solid rgba(243,186,47,.35)!important;background:linear-gradient(135deg,rgba(243,186,47,.22),rgba(255,255,255,.06))!important;color:#fff!important;transition:transform .18s ease}.stButton>button:active{transform:scale(.98)}.stTextInput input,.stNumberInput input,.stTextArea textarea,.stSelectbox div[data-baseweb="select"]{border-radius:16px!important;background:rgba(255,255,255,.06)!important;border-color:var(--line)!important;color:#fff!important;min-height:46px}.stMultiSelect div[data-baseweb="select"]{border-radius:16px!important;background:rgba(255,255,255,.06)!important}.stExpander{border:1px solid var(--line)!important;border-radius:22px!important;background:rgba(26,29,36,.5)!important;overflow:hidden}.skeleton{height:82px;border-radius:22px;background:linear-gradient(90deg,rgba(255,255,255,.05),rgba(255,255,255,.12),rgba(255,255,255,.05));background-size:220% 100%;animation:shimmer 1.4s infinite}.settings-title{font-size:1.2rem;margin:.1rem 0;letter-spacing:-.04em}.setting-row{padding:.75rem 0;border-bottom:1px solid var(--line)}div[role="radiogroup"]{position:fixed;left:50%;bottom:.55rem;transform:translateX(-50%);z-index:1000;width:min(410px,calc(100vw - 18px));display:grid!important;grid-template-columns:repeat(7,1fr);gap:.25rem;background:rgba(11,14,17,.86);border:1px solid var(--line);backdrop-filter:blur(24px);border-radius:24px;padding:.35rem;box-shadow:0 20px 50px rgba(0,0,0,.45)}div[role="radiogroup"] label{justify-content:center;border-radius:18px;padding:.38rem .1rem!important;margin:0!important;min-height:52px;background:transparent}div[role="radiogroup"] label:has(input:checked){background:linear-gradient(135deg,rgba(243,186,47,.25),rgba(255,255,255,.08))}div[role="radiogroup"] p{font-size:0!important}div[role="radiogroup"] p::first-letter{font-size:1.25rem!important}@keyframes shimmer{to{background-position:-220% 0}}@keyframes loadbar{from{width:0}}.float-in{animation:floatIn .5s cubic-bezier(.2,.8,.2,1) both}@keyframes floatIn{from{opacity:0;transform:translateY(14px) scale(.98)}to{opacity:1;transform:none}}@media(max-width:390px){div[role="radiogroup"] label{min-height:48px}.block-container{padding-left:.75rem!important;padding-right:.75rem!important}.value{font-size:1.9rem}.quick-grid,.metric-grid{gap:.45rem}.mini-stat,.metric-grid span{padding:.62rem .5rem}}
</style>
""",
    unsafe_allow_html=True,
)

client = CoinGeckoClient()
default_state = {"portfolio": empty_portfolio(), "watchlist": ["bitcoin", "ethereum", "solana"], "screen": "⌂", "currency": "USD", "theme": "Premium Dark", "refresh_interval": "90 secondes"}
for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

with st.sidebar:
    st.header("Studio de données")
    uploaded = st.file_uploader("Importer un CSV Spot", type=["csv"], help="Import éducatif uniquement. Aucune clé API ni exécution.")
    if uploaded is not None:
        try:
            imported = parse_binance_spot_csv(uploaded)
            if st.button("Utiliser le portefeuille importé", type="primary", use_container_width=True):
                st.session_state.portfolio = imported
                st.success(f"Importé {len(imported)} actifs.")
        except Exception as exc:
            st.warning(f"Import impossible : {html.escape(str(exc))}")
    st.divider()
    base_ids = set(st.session_state.portfolio.get("coin_id", pd.Series(dtype=str)).dropna().astype(str))
    default_ids = ", ".join(dict.fromkeys([*DEFAULT_COINS, *st.session_state.watchlist, *base_ids]))
    coin_ids_text = st.text_area("IDs CoinGecko", value=default_ids, height=120)
    include_trending = st.toggle("Inclure les tendances", value=True)
    refresh = st.button("Actualiser les données de marché", use_container_width=True)

coin_ids = [coin.strip().lower() for coin in coin_ids_text.replace("\n", ",").split(",") if coin.strip()]
if include_trending:
    try:
        coin_ids.extend(client.trending_ids())
    except Exception:
        st.sidebar.warning("Les tendances CoinGecko sont momentanément indisponibles.")
coin_ids = list(dict.fromkeys(coin_ids))

@st.cache_data(ttl=90, show_spinner=False)
def load_markets(ids: tuple[str, ...], currency: str) -> pd.DataFrame:
    return markets_to_frame(client.fetch_markets(ids, currency=currency.lower()))

try:
    if refresh:
        load_markets.clear()
    market_df = load_markets(tuple(coin_ids), st.session_state.currency)
except Exception:
    st.warning("Les données CoinGecko sont momentanément indisponibles. Réessaie dans quelques instants.")
    st.stop()
if market_df.empty:
    st.warning("Ajoute des IDs CoinGecko valides pour commencer."); st.stop()

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

st.markdown("<div class='topbar'><div class='hello'><p>Bonjour Mouad 👋</p><h1>Trader AI</h1></div><div class='top-actions'><span class='icon-btn'>↻</span><span class='icon-btn'>🔔</span></div></div>", unsafe_allow_html=True)
screen = st.radio("Navigation", ["⌂", "◌", "◎", "▣", "✦", "♡", "⚙"], horizontal=True, label_visibility="collapsed", key="screen")

if screen == "⌂":
    portfolio_placeholder = total_value <= 0
    portfolio_value_html = "Ajoute tes positions pour calculer ton portefeuille." if portfolio_placeholder else format_money(total_value)
    stats_html = (
        "<div class='mini-stat'><span>Portefeuille</span><b>En attente</b></div>"
        "<div class='mini-stat'><span>Performance</span><b>Ajoute tes positions</b></div>"
        "<div class='mini-stat'><span>Actualisation</span><b>90s</b></div>"
        if portfolio_placeholder
        else f"<div class='mini-stat'><span>P&L du jour</span><b class='{pct_class(daily_pnl)}'>{format_money(daily_pnl)}<br>{format_pct(daily_pnl_pct)}</b></div><div class='mini-stat'><span>Performance 24 h</span><b class='{pct_class(daily_pnl_pct)}'>{format_pct(daily_pnl_pct)}</b></div><div class='mini-stat'><span>Actualisation</span><b>90s</b></div>"
    )
    allocation_html = (
        "<p class='muted'>Ajoute tes positions pour calculer ton portefeuille.</p>"
        if portfolio_placeholder
        else "".join([f"<div class='allocation-pill'><b>{html.escape(str(r['symbol']))}</b><div class='allocation-bar'><i style='width:{safe_width(float(r['allocation_pct']))}%'></i></div><span>{format_pct(float(r['allocation_pct']))}</span></div>" for _, r in portfolio.head(6).iterrows()])
    )
    st.markdown(f"""
    <section class='portfolio-card float-in'><span class='eyebrow'>SOLDE DU PORTEFEUILLE</span><div class='value'>{portfolio_value_html}</div><div class='quick-grid'>{stats_html}</div>{sparkline_svg([sum((market_lookup.get(str(r['coin_id'])).sparkline[i] if market_lookup.get(str(r['coin_id'])) and len(market_lookup[str(r['coin_id'])].sparkline)>i else 0)*float(r['quantity']) for _, r in portfolio.iterrows()) for i in range(0, 42)] if not portfolio_placeholder else [])}<div class='metric-line'><span class='muted'>Notifications</span><b>{len(alerts)} actives</b></div></section>
    """, unsafe_allow_html=True)
    st.markdown("<section class='glass-card'><div class='section-head'><h2>Allocation du portefeuille</h2><span class='muted'>Répartition en direct</span></div><div class='allocation-list'>" + allocation_html + "</div></section>", unsafe_allow_html=True)
    if st.button("Actualisation", use_container_width=True):
        load_markets.clear(); st.rerun()
    for _, alert in alerts.iterrows():
        st.markdown(f"<div class='glass-card'>🔔 <b>{html.escape(str(alert['Asset']))}</b> {html.escape(str(alert['Alert']))} à {format_money(float(alert['Price']))}</div>", unsafe_allow_html=True)

elif screen == "◌":
    st.markdown("<div class='section-head'><h2>Portefeuille</h2><span class='muted'>Positions</span></div>", unsafe_allow_html=True)
    with st.expander("Ajouter ou modifier une position", expanded=portfolio.empty):
        with st.form("holding_form", clear_on_submit=False):
            coin_id = st.selectbox("Actif", options=market_ids, format_func=lambda cid: f"{market_lookup[cid].name} ({market_lookup[cid].symbol})")
            quantity = st.number_input("Quantité", min_value=0.0, step=0.0001, format="%.8f")
            avg_cost = st.number_input("Prix moyen", min_value=0.0, step=1.0, format="%.4f")
            c1, c2 = st.columns(2)
            alert_below = c1.number_input("Alerte sous", min_value=0.0, step=1.0, format="%.4f")
            alert_above = c2.number_input("Alerte au-dessus", min_value=0.0, step=1.0, format="%.4f")
            favorite = st.toggle("Favori", value=True)
            notes = st.text_input("Notes", placeholder="Stratégie, thèse ou rappel")
            if st.form_submit_button("Enregistrer la position", use_container_width=True):
                coin = market_lookup[coin_id]
                next_row = pd.DataFrame([{"coin_id": coin_id, "symbol": coin.symbol, "quantity": quantity, "avg_cost": avg_cost, "alert_below": alert_below, "alert_above": alert_above, "favorite": favorite, "notes": notes}])
                st.session_state.portfolio = normalize_portfolio(pd.concat([st.session_state.portfolio[st.session_state.portfolio["coin_id"] != coin_id], next_row], ignore_index=True)); st.rerun()
    for _, row in portfolio.iterrows():
        render_holding_card(row, market_lookup.get(str(row['coin_id'])))
    st.download_button("Exporter le portefeuille CSV", st.session_state.portfolio.to_csv(index=False), "trader_ai_portfolio.csv", "text/csv", use_container_width=True)

elif screen == "◎":
    st.markdown("<div class='section-head'><h2>Marchés</h2><span class='muted'>Cartes classées par IA</span></div>", unsafe_allow_html=True)
    selected_detail = st.selectbox("Ouvrir le détail", options=market_ids, format_func=lambda cid: f"{market_lookup[cid].name} ({market_lookup[cid].symbol})")
    coin = market_lookup[selected_detail]
    rec = recommendation_for(coin)
    support = min([coin.low_24h, *(coin.sparkline[-24:] or [coin.current_price])])
    resistance = max([coin.high_24h, *(coin.sparkline[-24:] or [coin.current_price])])
    st.markdown(f"<section class='glass-card'><div class='coin-row'><div class='coin-title'>{coin_logo(coin, coin.symbol)}<div><h2>{html.escape(coin.name)} — détail</h2><p>Vue de marché premium éducative</p></div></div>{score_badge(rec.opportunity_score)}</div><div class='chart-large'>{sparkline_svg(coin.sparkline, GREEN if coin.price_change_7d_pct >= 0 else RED)}</div><div class='metric-grid'><span>Support <b>{format_money(support)}</b></span><span>Résistance <b>{format_money(resistance)}</b></span><span>Volatilité <b>{volatility_pct(coin):.1f}%</b></span></div><p class='muted'><b>Analyse IA :</b> {html.escape(rec.rationale)}. Opportunité : {html.escape(ai_badge(rec.opportunity_score))}. Données CoinGecko uniquement, sans exécution d’ordre.</p><div class='metric-grid'><span>Momentum <b class='{pct_class(coin.price_change_7d_pct)}'>{format_pct(coin.price_change_7d_pct)}</b></span><span>Historique 30 j <b class='{pct_class(coin.price_change_30d_pct)}'>{format_pct(coin.price_change_30d_pct)}</b></span><span>Cap. marché <b>{format_money(coin.market_cap)}</b></span></div></section>", unsafe_allow_html=True)
    sort_by = st.selectbox("Trier les marchés", ["Rang de marché", "Score IA", "Gain 24 h", "Gain 7 j", "Volume"])
    coins = market_objects[:]
    if sort_by == "Score IA": coins.sort(key=lambda c: recommendation_for(c).opportunity_score, reverse=True)
    elif sort_by == "Gain 24 h": coins.sort(key=lambda c: c.price_change_24h_pct, reverse=True)
    elif sort_by == "Gain 7 j": coins.sort(key=lambda c: c.price_change_7d_pct, reverse=True)
    elif sort_by == "Volume": coins.sort(key=lambda c: c.total_volume, reverse=True)
    for coin in coins: render_market_card(coin, favorite=coin.coin_id in fav_ids or coin.coin_id in st.session_state.watchlist)

elif screen == "▣":
    st.markdown("<div class='section-head'><h2>Actualités</h2><span class='muted'>Dernières nouvelles CoinGecko</span></div>", unsafe_allow_html=True)
    @st.cache_data(ttl=300, show_spinner=False)
    def load_news() -> list[dict[str, object]]:
        return client.fetch_news(per_page=10)
    try:
        articles = load_news()
    except Exception:
        st.warning("Les actualités CoinGecko sont momentanément indisponibles. Aucune actualité ne peut être affichée pour l’instant.")
        articles = []
    if not articles:
        st.markdown("<section class='glass-card'><h3>Actualités indisponibles</h3><p class='muted'>CoinGecko ne renvoie pas d’actualités pour le moment. Le reste de l’application reste disponible avec les données de marché CoinGecko.</p></section>", unsafe_allow_html=True)
    for article in articles[:10]:
        title = html.escape(str(article.get('title') or 'Actualité du marché crypto'))
        source = html.escape(str(article.get('source') or article.get('source_name') or 'CoinGecko'))
        url = html.escape(str(article.get('url') or article.get('link') or '#'))
        st.markdown(f"<article class='glass-card news-card'><span class='eyebrow'>{source}</span><h3>{title}</h3><p class='muted'>{html.escape(one_sentence_summary(article))}</p><a href='{url}' target='_blank'>Lire l’article →</a></article>", unsafe_allow_html=True)

elif screen == "✦":
    st.markdown("<div class='section-head'><h2>Assistant IA</h2><span class='muted'>Analyse éducative</span></div>", unsafe_allow_html=True)
    best = max(market_objects, key=lambda c: recommendation_for(c).opportunity_score)
    riskiest = max(market_objects, key=volatility_pct)
    st.markdown(f"<section class='ai-card assistant-grid'><div class='assistant-card'><b>Résumé du marché</b><p class='muted'>Parmi les actifs suivis, {html.escape(best.name)} présente le meilleur score IA avec une performance 7 j de {format_pct(best.price_change_7d_pct)}. La lecture reste éducative et basée uniquement sur CoinGecko.</p></div><div class='assistant-card'><b>Meilleure opportunité</b><p class='muted'>{html.escape(best.name)} — {ai_badge(recommendation_for(best).opportunity_score)}. Raisons principales : {html.escape(recommendation_for(best).rationale)}.</p></div><div class='assistant-card'><b>Risque principal</b><p class='muted'>{html.escape(riskiest.name)} affiche la plage 24 h la plus large ({volatility_pct(riskiest):.1f}%). Réduis la taille des positions quand la volatilité augmente.</p></div><div class='assistant-card'><b>Conseil du jour</b><p class='muted'>Diversifie tes allocations, définis ton risque avant chaque décision et considère cette application comme un support pédagogique, pas comme un conseil financier.</p></div></section>", unsafe_allow_html=True)

elif screen == "♡":
    st.markdown("<div class='section-head'><h2>Liste de suivi</h2><span class='muted'>Cartes premium</span></div>", unsafe_allow_html=True)
    query = st.text_input("Rechercher", placeholder="Rechercher une crypto ou un symbole")
    picks = st.multiselect("Cryptos favorites", options=market_ids, default=[x for x in st.session_state.watchlist if x in market_ids], format_func=lambda cid: f"{market_lookup[cid].name} ({market_lookup[cid].symbol})")
    st.session_state.watchlist = picks
    filter_mode = st.selectbox("Filtrer", ["Toutes", "En hausse", "En baisse", "Score IA élevé", "Risque faible"])
    sort_mode = st.selectbox("Trier", ["Score IA", "Rang", "24h", "7j"])
    watch_coins = [market_lookup[cid] for cid in dict.fromkeys([*picks, *fav_ids]) if cid in market_lookup and (not query or query.lower() in market_lookup[cid].name.lower() or query.lower() in market_lookup[cid].symbol.lower())]
    if filter_mode == "En hausse": watch_coins = [c for c in watch_coins if c.price_change_24h_pct >= 0]
    elif filter_mode == "En baisse": watch_coins = [c for c in watch_coins if c.price_change_24h_pct < 0]
    elif filter_mode == "Score IA élevé": watch_coins = [c for c in watch_coins if recommendation_for(c).opportunity_score >= 60]
    elif filter_mode == "Risque faible": watch_coins = [c for c in watch_coins if risk_label(c)[0] == "Faible"]
    if sort_mode == "Score IA": watch_coins.sort(key=lambda c: recommendation_for(c).opportunity_score, reverse=True)
    elif sort_mode == "Rang": watch_coins.sort(key=lambda c: c.market_cap_rank or 9999)
    elif sort_mode == "24h": watch_coins.sort(key=lambda c: c.price_change_24h_pct, reverse=True)
    else: watch_coins.sort(key=lambda c: c.price_change_7d_pct, reverse=True)
    for coin in watch_coins: render_market_card(coin, favorite=True)

else:
    st.markdown("<section class='glass-card'><h2 class='settings-title'>Réglages</h2><p class='muted'>Thème premium sombre, données CoinGecko uniquement, aucune API Binance, aucune exécution d’ordre, usage éducatif uniquement.</p></section>", unsafe_allow_html=True)
    st.session_state.theme = st.selectbox("Thème", ["Premium Dark"], index=0)
    st.session_state.currency = st.selectbox("Devise", ["USD", "EUR", "GBP"], index=["USD", "EUR", "GBP"].index(st.session_state.currency))
    notifications = st.toggle("Notifications", value=True)
    st.session_state.refresh_interval = st.selectbox("Intervalle d’actualisation", ["60 secondes", "90 secondes", "5 minutes"], index=["60 secondes", "90 secondes", "5 minutes"].index(st.session_state.refresh_interval))
    st.markdown(f"<section class='glass-card'><div class='setting-row'><span>À propos</span><b>{APP_NAME} v{APP_VERSION}</b></div><div class='setting-row'><span>Notifications</span><b>{'Activées' if notifications else 'Désactivées'}</b></div><div class='setting-row'><span>Source des données</span><b>CoinGecko uniquement</b></div><p class='muted'><b>Avertissement éducatif :</b> Trader AI sert uniquement à l’éducation et à la recherche de marché. L’application ne fournit pas de conseil financier, n’exécute aucun ordre, ne se connecte pas à Binance et ne conserve aucun actif.</p></section>", unsafe_allow_html=True)
