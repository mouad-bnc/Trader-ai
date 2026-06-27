from __future__ import annotations

import html
import math
from typing import Iterable

import pandas as pd
import streamlit as st

from binance import BinanceReadOnlyClient
from coingecko import DEFAULT_COINS, CoinGeckoClient, MarketCoin, markets_to_frame
from portfolio_analytics import enrich_portfolio, format_money, format_pct, recommendation_for, triggered_alerts
from portfolio_io import empty_portfolio, normalize_portfolio, parse_binance_spot_csv

APP_NAME = "Mouad Saissi - Trader"
APP_VERSION = "5.0"
GOLD = "#F3BA2F"
GREEN = "#02C076"
RED = "#F6465D"

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



@st.cache_data(ttl=900, show_spinner=False)
def fear_greed() -> tuple[int | None, str]:
    """Read the public Fear & Greed index instead of inventing a value."""
    try:
        import requests
        response = requests.get("https://api.alternative.me/fng/", params={"limit": 1, "format": "json"}, timeout=8)
        response.raise_for_status()
        payload = response.json()
        latest = (payload.get("data") or [{}])[0]
        return int(latest.get("value")), str(latest.get("value_classification") or "Marché")
    except Exception:
        return None, "Indisponible"


def btc_dominance(markets: list[MarketCoin]) -> float:
    total = sum(max(coin.market_cap, 0) for coin in markets)
    btc = next((coin.market_cap for coin in markets if coin.coin_id == "bitcoin"), 0)
    return (btc / total * 100) if total else 0


def segment_allocation(total: float) -> dict[str, float]:
    if total <= 0:
        return {"Spot": 0, "Earn": 0, "Bots": 0}
    return {"Spot": total * .72, "Earn": total * .18, "Bots": total * .10}


def signal_label(score: int) -> str:
    if score >= 78: return "Acheter"
    if score >= 64: return "Renforcer"
    if score >= 50: return "Surveiller"
    if score >= 38: return "Conserver"
    return "Éviter"


def demo_news() -> list[dict[str, object]]:
    """Return no synthetic news; the UI renders a premium empty state instead."""
    return []

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
            <div class="price-stack"><button class="fav" aria-label="favori">{heart}</button><strong>{format_money(coin.current_price)}</strong><span class="{pct_class(coin.price_change_24h_pct)}">{trend_arrow} 24h {format_pct(coin.price_change_24h_pct)}</span></div>
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
:root{--bg:#0B0E11;--surface:#181A20;--surface-2:#1E2329;--gold:#F3BA2F;--green:#02C076;--red:#F6465D;--text:#fff;--muted:#A7B0BE;--line:rgba(255,255,255,.08);--shadow:0 16px 45px rgba(0,0,0,.28)}
.stApp{background:radial-gradient(circle at 10% -8%,rgba(243,186,47,.16),transparent 30%),linear-gradient(180deg,var(--bg) 0%,#080A0D 100%);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Inter",sans-serif}.block-container{max-width:430px!important;padding:calc(env(safe-area-inset-top) + 7.2rem) .95rem calc(env(safe-area-inset-bottom) + 1.8rem)!important;overflow-x:hidden}#MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="stDecoration"],.stDeployButton{display:none!important}.stApp *{box-sizing:border-box}.app-shell{position:fixed;z-index:1000;top:0;left:50%;transform:translateX(-50%);width:min(430px,100vw);padding:calc(env(safe-area-inset-top) + .45rem) .65rem .45rem;background:linear-gradient(180deg,rgba(11,14,17,.98),rgba(11,14,17,.86));backdrop-filter:blur(24px);border-bottom:1px solid var(--line)}.topbar{height:44px;display:flex;align-items:center;justify-content:space-between;gap:.7rem}.brand{font-size:1.05rem;font-weight:900;letter-spacing:-.04em}.nav-icons{display:flex;gap:.45rem}.icon-btn{width:38px;height:38px;border:1px solid var(--line);border-radius:15px;background:rgba(255,255,255,.055);display:grid;place-items:center}.tabs{display:none}.section-title{font-size:1.25rem;letter-spacing:-.045em;margin:.2rem 0 .75rem}.hero h1{font-size:1.45rem;letter-spacing:-.055em;margin:.15rem 0}.muted,.hero p,.coin-title p,.mini-stat span{color:var(--muted);font-size:.76rem;margin:.12rem 0}.portfolio-card,.coin-card,.glass-card,.ai-card,.empty-card,.news-card{border-radius:22px;background:linear-gradient(145deg,rgba(255,255,255,.065),rgba(255,255,255,.025)),var(--surface);border:1px solid var(--line);box-shadow:var(--shadow),inset 0 1px 0 rgba(255,255,255,.06);padding:1rem;margin:.78rem 0;overflow:hidden;animation:fadeSlide .34s ease both}.portfolio-card{background:radial-gradient(circle at 12% 0%,rgba(243,186,47,.25),transparent 42%),linear-gradient(145deg,#22262E,#11141A)}.empty-card{text-align:left;background:linear-gradient(145deg,rgba(243,186,47,.09),rgba(255,255,255,.025)),var(--surface)}.empty-icon{width:52px;height:52px;border-radius:18px;background:rgba(243,186,47,.15);display:grid;place-items:center;color:var(--gold);font-size:1.35rem;margin-bottom:.7rem}.eyebrow,.pill{display:inline-flex;align-items:center;gap:.35rem;color:#161102;background:linear-gradient(135deg,var(--gold),#FFE29A);font-weight:900;font-size:.66rem;border-radius:999px;padding:.28rem .55rem}.pill{background:rgba(255,255,255,.06);color:#EAECEF;border:1px solid var(--line)}.value{font-size:2.2rem;font-weight:950;letter-spacing:-.075em;margin:.55rem 0 .25rem}.quick-grid,.metric-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.55rem}.mini-stat,.metric-grid span{background:rgba(0,0,0,.20);border:1px solid var(--line);border-radius:17px;padding:.68rem .58rem;min-width:0}.mini-stat b,.metric-grid b{display:block;font-size:.84rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.section-head,.coin-row,.coin-title,.metric-line,.progress-row{display:flex;align-items:center;justify-content:space-between;gap:.72rem}.positive,.risk-low{color:var(--green)!important}.negative,.risk-high{color:var(--red)!important}.risk-med{color:var(--gold)!important}.sparkline{width:100%;height:70px;margin:.75rem 0}.coin-card{transition:transform .24s ease,border-color .24s ease}.coin-card:active,.stButton>button:active{transform:scale(.985)}.coin-logo,.coin-fallback{width:42px;height:42px;border-radius:50%;box-shadow:0 0 0 1px rgba(255,255,255,.12)}.coin-fallback{display:grid;place-items:center;background:linear-gradient(135deg,var(--gold),#8b681d);color:#111;font-weight:900}.coin-title{justify-content:flex-start}.coin-title h3{font-size:1rem;letter-spacing:-.04em;margin:0}.price-stack{text-align:right;display:flex;align-items:flex-end;flex-direction:column;gap:.15rem}.price-stack strong{font-size:.98rem}.price-stack span{font-size:.7rem}.fav{width:30px;height:30px;border-radius:11px;color:var(--gold);background:rgba(255,255,255,.06);border:1px solid var(--line)}.badge-row,.suggestions{display:flex;gap:.45rem;flex-wrap:wrap;margin-top:.7rem}.badge-row em,.suggestions span{font-style:normal;font-weight:800;font-size:.68rem;padding:.34rem .55rem;border-radius:999px;border:1px solid rgba(243,186,47,.25);background:rgba(243,186,47,.12);color:#FFE29A}.score-badge{min-width:62px;height:46px;border-radius:16px;display:flex;align-items:center;justify-content:center;gap:.1rem;flex-direction:column;background:linear-gradient(135deg,var(--gold),#74551a);color:#0B0E11}.progress,.volatility{height:8px;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden;margin:.35rem 0 .7rem}.progress i,.volatility i{display:block;height:100%;background:linear-gradient(90deg,#8A6419,var(--gold),#FFF2BF);border-radius:999px;animation:loadbar .8s ease}.stButton>button,.stDownloadButton>button{border-radius:17px!important;min-height:46px!important;border:1px solid rgba(243,186,47,.35)!important;background:linear-gradient(135deg,rgba(243,186,47,.24),rgba(255,255,255,.06))!important;color:#fff!important}.stTextInput input,.stNumberInput input,.stTextArea textarea,.stSelectbox div[data-baseweb="select"]{border-radius:16px!important;background:rgba(255,255,255,.06)!important;border-color:var(--line)!important;color:#fff!important;min-height:46px}.stExpander{border:1px solid var(--line)!important;border-radius:22px!important;background:rgba(24,26,32,.72)!important;overflow:hidden}div[role="radiogroup"]{position:fixed;left:50%;top:calc(env(safe-area-inset-top) + 3.72rem);transform:translateX(-50%);z-index:1001;width:min(410px,calc(100vw - 20px));height:52px;max-height:56px;display:flex!important;flex-wrap:nowrap;align-items:center;gap:.4rem;overflow-x:auto;overflow-y:hidden;background:transparent;padding:.25rem .05rem;scrollbar-width:none;-ms-overflow-style:none;white-space:nowrap;touch-action:pan-x}div[role="radiogroup"]::-webkit-scrollbar{display:none}div[role="radiogroup"] label{flex:0 0 auto;justify-content:center;border:1px solid transparent;border-radius:999px;padding:.48rem .84rem!important;margin:0!important;min-height:40px;min-width:max-content;background:transparent;white-space:nowrap}div[role="radiogroup"] label:has(input:checked){background:rgba(243,186,47,.16);border-color:rgba(243,186,47,.28);color:#fff}div[role="radiogroup"] p{font-size:.78rem!important;font-weight:850;line-height:1!important;white-space:nowrap}.donut{width:152px;height:152px;border-radius:50%;background:conic-gradient(var(--gold) 0 var(--a,58%), var(--green) var(--a,58%) var(--b,82%), #5561ff var(--b,82%));margin:.5rem auto;display:grid;place-items:center}.donut:after{content:"";width:92px;height:92px;border-radius:50%;background:#11141b}.chat-bubble{white-space:pre-line;border-radius:22px;padding:.88rem;margin:.58rem 0;max-width:92%;border:1px solid var(--line);line-height:1.45}.bot{background:rgba(243,186,47,.12)}.user{background:rgba(255,255,255,.07);margin-left:auto}.avatar{width:34px;height:34px;border-radius:14px;background:var(--gold);color:#111;display:inline-grid;place-items:center;font-weight:900;margin-right:.45rem}.news-img{height:118px;border-radius:18px;background:linear-gradient(135deg,rgba(243,186,47,.22),rgba(2,192,118,.10)),var(--surface-2);background-size:cover;background-position:center;margin-bottom:.7rem}.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 0 4px rgba(2,192,118,.12)}@keyframes loadbar{from{width:0}}@keyframes fadeSlide{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}@media(max-width:390px){.block-container{padding-left:.75rem!important;padding-right:.75rem!important}.value{font-size:1.9rem}.quick-grid,.metric-grid{gap:.42rem}.mini-stat,.metric-grid span{padding:.58rem .48rem}}
</style>
""",
    unsafe_allow_html=True,
)

client = CoinGeckoClient()
default_state = {"portfolio": empty_portfolio(), "watchlist": ["bitcoin", "ethereum", "solana"], "screen": "Accueil", "currency": "USD", "theme": "Premium Dark", "refresh_interval": "90 secondes"}
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

st.markdown(f"<div class='app-shell'><div class='topbar'><span class='icon-btn'>☰</span><div class='brand'>{html.escape(APP_NAME)}</div><div class='nav-icons'><span class='icon-btn'>🔔</span><span class='icon-btn'>👤</span></div></div></div>", unsafe_allow_html=True)
sections = ["Accueil", "Marchés", "Wallet", "Bots", "News", "Calculateur", "Opportunités", "IA"]
screen = st.radio("Navigation", sections, horizontal=True, label_visibility="collapsed", key="screen")
fng_value, fng_label = fear_greed()
dominance = btc_dominance(market_objects)
segments = segment_allocation(total_value)
fng_display = f"{fng_value}/100" if fng_value is not None else "Indisponible"

if screen == "Accueil":
    st.markdown("<div class='hero'><p>Bonjour Mouad 👋</p><h1>Votre cockpit crypto</h1></div>", unsafe_allow_html=True)
    top_gain = best_row.iloc[0] if not best_row.empty else None
    top_loss = worst_row.iloc[0] if not worst_row.empty else None
    if portfolio.empty and not BinanceReadOnlyClient().configured:
        st.markdown("""<section class='empty-card'><div class='empty-icon'>⌁</div><h2>Connectez Binance pour afficher votre portefeuille.</h2><p class='muted'>Vos soldes, votre allocation et votre PnL apparaîtront ici dès qu'une connexion lecture seule sera disponible.</p></section>""", unsafe_allow_html=True)
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

elif screen == "Marchés":
    st.markdown(f"<section class='glass-card'><div class='section-head'><h2>Marchés</h2><span class='muted'>Fear & Greed {fng_display} · BTC {dominance:.1f}%</span></div></section>", unsafe_allow_html=True)
    query = st.text_input("Recherche crypto", placeholder="BTC, ETH, SOL…")
    filtered = [c for c in market_objects if not query or query.lower() in c.name.lower() or query.upper() in c.symbol]
    st.markdown("<h3>Meilleures hausses</h3>", unsafe_allow_html=True)
    for coin in sorted(filtered, key=lambda c: c.price_change_24h_pct, reverse=True)[:3]: render_market_card(coin, favorite=coin.coin_id in st.session_state.watchlist)
    st.markdown("<h3>Plus fortes baisses</h3>", unsafe_allow_html=True)
    for coin in sorted(filtered, key=lambda c: c.price_change_24h_pct)[:3]: render_market_card(coin, favorite=coin.coin_id in st.session_state.watchlist)
    st.markdown("<h3>Liste de suivi</h3>", unsafe_allow_html=True)
    for coin in [c for c in filtered if c.coin_id in st.session_state.watchlist][:5]: render_market_card(coin, favorite=True)

elif screen == "Wallet":
    binance = BinanceReadOnlyClient()
    if portfolio.empty:
        st.markdown("<section class='empty-card'><div class='empty-icon'>◒</div><h2>Votre portefeuille est prêt.</h2><p class='muted'>Connectez Binance ou ajoutez une position pour afficher la valeur totale, l'allocation, le donut et la liste des actifs.</p></section>", unsafe_allow_html=True)
    else:
        st.markdown(f"<section class='portfolio-card'><span class='eyebrow'>PORTEFEUILLE</span><div class='value'>{format_money(total_value)}</div><div class='donut'></div><div class='quick-grid'><div class='mini-stat'><span>Spot</span><b>{format_money(total_value)}</b></div><div class='mini-stat'><span>Allocation</span><b>{len(portfolio)} actifs</b></div><div class='mini-stat'><span>PnL</span><b class='{pct_class(total_pnl)}'>{format_pct(total_pnl_pct)}</b></div></div></section>", unsafe_allow_html=True)
    if not binance.configured:
        st.markdown("<section class='empty-card'><div class='section-head'><h3>Binance</h3><span class='pill'>Hors ligne</span></div><p class='muted'>API absente. Activez une clé lecture seule pour synchroniser automatiquement vos soldes Spot.</p></section>", unsafe_allow_html=True)
        st.button("Connecter Binance", use_container_width=True)
    else:
        try:
            assets = binance.spot_assets()
            st.markdown("<h3>Binance Spot lecture seule</h3>", unsafe_allow_html=True)
            for asset in assets[:12]:
                st.markdown(f"<div class='glass-card'><div class='metric-line'><b>{asset.symbol}</b><span>{asset.quantity:,.8f}</span></div><div class='metric-line'><span>Prix actuel</span><b>{format_money(asset.current_price)}</b></div><div class='metric-line'><span>Valeur</span><b>{format_money(asset.value)}</b></div></div>", unsafe_allow_html=True)
        except Exception as exc:
            st.warning(f"Lecture Binance indisponible : {html.escape(str(exc))}")
    with st.expander("Ajouter ou modifier une position", expanded=portfolio.empty):
        with st.form("holding_form", clear_on_submit=False):
            coin_id = st.selectbox("Actif", options=market_ids, format_func=lambda cid: f"{market_lookup[cid].name} ({market_lookup[cid].symbol})")
            quantity = st.number_input("Quantité", min_value=0.0, step=0.0001, format="%.8f")
            avg_cost = st.number_input("Prix moyen", min_value=0.0, step=1.0, format="%.4f")
            favorite = st.toggle("Favori", value=True)
            if st.form_submit_button("Enregistrer la position", use_container_width=True):
                coin = market_lookup[coin_id]
                next_row = pd.DataFrame([{"coin_id": coin_id, "symbol": coin.symbol, "quantity": quantity, "avg_cost": avg_cost, "alert_below": 0, "alert_above": 0, "favorite": favorite, "notes": ""}])
                st.session_state.portfolio = normalize_portfolio(pd.concat([st.session_state.portfolio[st.session_state.portfolio["coin_id"] != coin_id], next_row], ignore_index=True)); st.rerun()
    for _, row in portfolio.iterrows(): render_holding_card(row, market_lookup.get(str(row['coin_id'])))

elif screen == "Bots":
    st.markdown("<section class='empty-card'><div class='empty-icon'>⌘</div><h2>Bots</h2><p class='muted'>Aucun bot connecté. Les performances réelles s'afficheront uniquement après connexion d'une source de données.</p></section>", unsafe_allow_html=True)

elif screen == "News":
    @st.cache_data(ttl=300, show_spinner=False)
    def load_news() -> list[dict[str, object]]: return client.fetch_news(per_page=10)
    try: articles = load_news() or demo_news()
    except Exception: articles = demo_news()
    if not articles:
        st.markdown("<section class='empty-card'><div class='empty-icon'>▧</div><h2>Feed indisponible</h2><p class='muted'>Aucune actualité vérifiée n'est disponible pour le moment. Réessayez après la prochaine synchronisation.</p></section>", unsafe_allow_html=True)
    for article in articles[:10]:
        tags = article.get('tags') or [tag for tag in ['BTC','ETH','SOL','DOGE','SUI'] if tag.lower() in str(article).lower()] or ['Crypto']
        image = html.escape(str(article.get('thumb_2x') or article.get('image') or article.get('urlToImage') or ''))
        image_style = f" style=\"background-image:url('{image}')\"" if image else ""
        source = html.escape(str(article.get('source') or article.get('source_name') or 'Source crypto'))
        st.markdown(f"<article class='news-card'><div class='news-img'{image_style}></div><span class='eyebrow'>{source}</span><h3>{html.escape(str(article.get('title') or 'Actualité crypto'))}</h3><p class='muted'>{html.escape(str(article.get('date') or article.get('created_at') or 'Maintenant'))}</p><p>{html.escape(one_sentence_summary(article))}</p><div class='badge-row'>{''.join(f'<em>{html.escape(str(t))}</em>' for t in tags)}</div></article>", unsafe_allow_html=True)

elif screen == "Calculateur":
    st.markdown("<section class='glass-card'><h2>Calculateur</h2><p class='muted'>Résultat instantané.</p></section>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    capital = c1.number_input("Capital", min_value=0.0, value=1000.0)
    prix = c2.number_input("Prix actuel", min_value=0.000001, value=100.0, format="%.6f")
    entree = c1.number_input("Prix d’entrée", min_value=0.000001, value=90.0, format="%.6f")
    sortie = c2.number_input("Objectif gain", min_value=0.000001, value=120.0, format="%.6f")
    stop = c1.number_input("Seuil de protection", min_value=0.000001, value=80.0, format="%.6f")
    dca = c2.number_input("Achat DCA", min_value=0.0, value=250.0)
    qty = capital / entree if entree else 0
    avg = (capital + dca) / (qty + dca / prix) if prix and qty + dca / prix else entree
    roi = (sortie - avg) / avg * 100
    risk = max(avg - stop, 0); reward = max(sortie - avg, 0)
    st.markdown(f"<section class='portfolio-card'><div class='metric-grid'><span>Prix moyen <b>{format_money(avg)}</b></span><span>DCA <b>{format_money(dca)}</b></span><span>ROI <b class='{pct_class(roi)}'>{format_pct(roi)}</b></span><span>Ratio risque/rendement <b>{(reward/risk if risk else 0):.2f}</b></span><span>Taille position <b>{qty:.6f}</b></span><span>Seuil de protection <b>{format_money(stop)}</b></span></div></section>", unsafe_allow_html=True)

elif screen == "Opportunités":
    st.markdown("<section class='glass-card'><h2>Opportunités</h2><p class='notice'>Analyse indicative uniquement.</p></section>", unsafe_allow_html=True)
    for coin in sorted(market_objects, key=lambda c: recommendation_for(c).opportunity_score, reverse=True)[:12]:
        rec = recommendation_for(coin); conf = confidence_for(coin)
        st.markdown(f"<article class='coin-card'><div class='coin-row'><div class='coin-title'>{coin_logo(coin, coin.symbol)}<div><h3>{coin.name}</h3><p>{coin.symbol}</p></div></div>{score_badge(rec.opportunity_score)}</div><div class='metric-grid'><span>Signal <b>{signal_label(rec.opportunity_score)}</b></span><span>Confiance <b>{conf}%</b></span><span>Prix <b>{format_money(coin.current_price)}</b></span></div><p class='muted'>{html.escape(rec.rationale)}</p></article>", unsafe_allow_html=True)

else:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "bot", "text": "Bonjour Mouad 👋\n\nJe suis Trader.\n\nJe peux analyser :\n• ton portefeuille\n• le marché\n• une crypto\n• les news\n• les opportunités."}]
    for msg in st.session_state.messages:
        st.markdown(f"<div class='chat-bubble {'bot' if msg['role']=='bot' else 'user'}'>{html.escape(msg['text'])}</div>", unsafe_allow_html=True)
    prompt = st.text_input("Message", placeholder="Demandez à Trader d’analyser votre portefeuille...")
    for suggestion in ["Analyser mon portefeuille", "Faut-il acheter SOL ?", "DOGE est-il encore intéressant ?", "Meilleure opportunité aujourd’hui", "Calculer mon prix moyen"]:
        if st.button(suggestion, use_container_width=True): prompt = suggestion
    if prompt:
        best = max(market_objects, key=lambda c: recommendation_for(c).opportunity_score)
        st.session_state.messages.append({"role":"user","text":prompt})
        st.session_state.messages.append({"role":"bot","text":f"Analyse indicative : {best.name} obtient le meilleur score actuel ({recommendation_for(best).opportunity_score}/100). Vérifie toujours ton risque, ton prix moyen et ton stop avant toute décision."})
        st.rerun()
