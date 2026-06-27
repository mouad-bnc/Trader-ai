from __future__ import annotations

import html
import math
from typing import Iterable

import pandas as pd
import streamlit as st

from services.market_service import DEFAULT_COINS, MarketCoin, MarketService
from components.badges import score_badge
from components.cards import coin_logo, render_holding_card as component_holding_card, render_market_card as component_market_card
from portfolio_analytics import format_money, format_pct, recommendation_for
from services.news_service import NewsService
from services.portfolio_service import PortfolioService
from pages.bots import render_bots
from pages.calculator import render_calculator
from pages.home import render_home
from pages.markets import render_markets
from pages.news import render_news
from pages.opportunities import render_opportunities
from pages.portfolio import render_portfolio
from pages.trader_ai import render_trader_ai

APP_NAME = "Mouad Saissi - Trader"
APP_VERSION = "5.0"
GOLD = "#F3BA2F"
GREEN = "#02C076"
RED = "#F6465D"
SECTIONS = ["Accueil", "Marchés", "Portefeuille", "Bots", "Actualités", "Calculateur", "Opportunités", "Trader IA"]

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
    component_market_card(
        coin,
        owned_value=owned_value,
        favorite=favorite,
        pct_class=pct_class,
        sparkline_svg=sparkline_svg,
        risk_label=risk_label,
        ai_badge=ai_badge,
        confidence_for=confidence_for,
        volatility_pct=volatility_pct,
        safe_width=safe_width,
    )


def render_holding_card(row: pd.Series, coin: MarketCoin | None) -> None:
    component_holding_card(row, coin, pct_class=pct_class, sparkline_svg=sparkline_svg)



st.markdown(
    """
<style>
:root{--bg:#0B0E11;--surface:#181A20;--surface-2:#1E2329;--gold:#F3BA2F;--green:#02C076;--red:#F6465D;--text:#fff;--muted:#A7B0BE;--line:rgba(255,255,255,.08);--shadow:0 16px 45px rgba(0,0,0,.28)}
.stApp{background:radial-gradient(circle at 10% -8%,rgba(243,186,47,.16),transparent 30%),linear-gradient(180deg,var(--bg) 0%,#080A0D 100%);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Inter",sans-serif}.block-container{max-width:430px!important;padding:calc(env(safe-area-inset-top) + 7.2rem) .95rem calc(env(safe-area-inset-bottom) + 1.8rem)!important;overflow-x:hidden}#MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="stDecoration"],.stDeployButton{display:none!important}.stApp *{box-sizing:border-box}.app-shell{position:fixed;z-index:1000;top:0;left:50%;transform:translateX(-50%);width:min(430px,100vw);padding:calc(env(safe-area-inset-top) + .45rem) .65rem .45rem;background:linear-gradient(180deg,rgba(11,14,17,.98),rgba(11,14,17,.86));backdrop-filter:blur(24px);border-bottom:1px solid var(--line)}.topbar{height:44px;display:flex;align-items:center;justify-content:space-between;gap:.7rem}.brand{font-size:1.05rem;font-weight:900;letter-spacing:-.04em}.nav-icons{display:flex;gap:.45rem}.icon-btn{width:38px;height:38px;border:1px solid var(--line);border-radius:15px;background:rgba(255,255,255,.055);display:grid;place-items:center}.tabs{display:none}.section-title{font-size:1.25rem;letter-spacing:-.045em;margin:.2rem 0 .75rem}.hero h1{font-size:1.45rem;letter-spacing:-.055em;margin:.15rem 0}.muted,.hero p,.coin-title p,.mini-stat span{color:var(--muted);font-size:.76rem;margin:.12rem 0}.portfolio-card,.coin-card,.glass-card,.ai-card,.empty-card,.news-card{border-radius:22px;background:linear-gradient(145deg,rgba(255,255,255,.065),rgba(255,255,255,.025)),var(--surface);border:1px solid var(--line);box-shadow:var(--shadow),inset 0 1px 0 rgba(255,255,255,.06);padding:1rem;margin:.78rem 0;overflow:hidden;animation:fadeSlide .34s ease both}.portfolio-card{background:radial-gradient(circle at 12% 0%,rgba(243,186,47,.25),transparent 42%),linear-gradient(145deg,#22262E,#11141A)}.empty-card{text-align:left;background:linear-gradient(145deg,rgba(243,186,47,.09),rgba(255,255,255,.025)),var(--surface)}.empty-icon{width:52px;height:52px;border-radius:18px;background:rgba(243,186,47,.15);display:grid;place-items:center;color:var(--gold);font-size:1.35rem;margin-bottom:.7rem}.eyebrow,.pill{display:inline-flex;align-items:center;gap:.35rem;color:#161102;background:linear-gradient(135deg,var(--gold),#FFE29A);font-weight:900;font-size:.66rem;border-radius:999px;padding:.28rem .55rem}.pill{background:rgba(255,255,255,.06);color:#EAECEF;border:1px solid var(--line)}.value{font-size:2.2rem;font-weight:950;letter-spacing:-.075em;margin:.55rem 0 .25rem}.quick-grid,.metric-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.55rem}.mini-stat,.metric-grid span{background:rgba(0,0,0,.20);border:1px solid var(--line);border-radius:17px;padding:.68rem .58rem;min-width:0}.mini-stat b,.metric-grid b{display:block;font-size:.84rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.section-head,.coin-row,.coin-title,.metric-line,.progress-row{display:flex;align-items:center;justify-content:space-between;gap:.72rem}.positive,.risk-low{color:var(--green)!important}.negative,.risk-high{color:var(--red)!important}.risk-med{color:var(--gold)!important}.sparkline{width:100%;height:70px;margin:.75rem 0}.coin-card{transition:transform .24s ease,border-color .24s ease}.coin-card:active,.stButton>button:active{transform:scale(.985)}.coin-logo,.coin-fallback{width:42px;height:42px;border-radius:50%;box-shadow:0 0 0 1px rgba(255,255,255,.12)}.coin-fallback{display:grid;place-items:center;background:linear-gradient(135deg,var(--gold),#8b681d);color:#111;font-weight:900}.coin-title{justify-content:flex-start}.coin-title h3{font-size:1rem;letter-spacing:-.04em;margin:0}.price-stack{text-align:right;display:flex;align-items:flex-end;flex-direction:column;gap:.15rem}.price-stack strong{font-size:.98rem}.price-stack span{font-size:.7rem}.fav{width:30px;height:30px;border-radius:11px;color:var(--gold);background:rgba(255,255,255,.06);border:1px solid var(--line)}.badge-row,.suggestions{display:flex;gap:.45rem;flex-wrap:wrap;margin-top:.7rem}.badge-row em,.suggestions span{font-style:normal;font-weight:800;font-size:.68rem;padding:.34rem .55rem;border-radius:999px;border:1px solid rgba(243,186,47,.25);background:rgba(243,186,47,.12);color:#FFE29A}.score-badge{min-width:62px;height:46px;border-radius:16px;display:flex;align-items:center;justify-content:center;gap:.1rem;flex-direction:column;background:linear-gradient(135deg,var(--gold),#74551a);color:#0B0E11}.progress,.volatility{height:8px;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden;margin:.35rem 0 .7rem}.progress i,.volatility i{display:block;height:100%;background:linear-gradient(90deg,#8A6419,var(--gold),#FFF2BF);border-radius:999px;animation:loadbar .8s ease}.stButton>button,.stDownloadButton>button{border-radius:17px!important;min-height:46px!important;border:1px solid rgba(243,186,47,.35)!important;background:linear-gradient(135deg,rgba(243,186,47,.24),rgba(255,255,255,.06))!important;color:#fff!important}.stTextInput input,.stNumberInput input,.stTextArea textarea,.stSelectbox div[data-baseweb="select"]{border-radius:16px!important;background:rgba(255,255,255,.06)!important;border-color:var(--line)!important;color:#fff!important;min-height:46px}.stExpander{border:1px solid var(--line)!important;border-radius:22px!important;background:rgba(24,26,32,.72)!important;overflow:hidden}div[role="radiogroup"]{position:fixed;left:50%;top:calc(env(safe-area-inset-top) + 3.72rem);transform:translateX(-50%);z-index:1001;width:min(410px,calc(100vw - 20px));height:52px;max-height:56px;display:flex!important;flex-wrap:nowrap;align-items:center;gap:.4rem;overflow-x:auto;overflow-y:hidden;background:transparent;padding:.25rem .05rem;scrollbar-width:none;-ms-overflow-style:none;white-space:nowrap;touch-action:pan-x}div[role="radiogroup"]::-webkit-scrollbar{display:none}div[role="radiogroup"] label{flex:0 0 auto;justify-content:center;border:1px solid transparent;border-radius:999px;padding:.48rem .84rem!important;margin:0!important;min-height:40px;min-width:max-content;background:transparent;white-space:nowrap}div[role="radiogroup"] label:has(input:checked){background:rgba(243,186,47,.16);border-color:rgba(243,186,47,.28);color:#fff}div[role="radiogroup"] p{font-size:.78rem!important;font-weight:850;line-height:1!important;white-space:nowrap}.donut{width:152px;height:152px;border-radius:50%;background:conic-gradient(var(--gold) 0 var(--a,58%), var(--green) var(--a,58%) var(--b,82%), #5561ff var(--b,82%));margin:.5rem auto;display:grid;place-items:center}.donut:after{content:"";width:92px;height:92px;border-radius:50%;background:#11141b}.chat-bubble{white-space:pre-line;border-radius:22px;padding:.88rem;margin:.58rem 0;max-width:92%;border:1px solid var(--line);line-height:1.45}.bot{background:rgba(243,186,47,.12)}.user{background:rgba(255,255,255,.07);margin-left:auto}.avatar{width:34px;height:34px;border-radius:14px;background:var(--gold);color:#111;display:inline-grid;place-items:center;font-weight:900;margin-right:.45rem}.news-img{height:118px;border-radius:18px;background:linear-gradient(135deg,rgba(243,186,47,.22),rgba(2,192,118,.10)),var(--surface-2);background-size:cover;background-position:center;margin-bottom:.7rem}.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 0 4px rgba(2,192,118,.12)}@keyframes loadbar{from{width:0}}@keyframes fadeSlide{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}@media(max-width:390px){.block-container{padding-left:.75rem!important;padding-right:.75rem!important}.value{font-size:1.9rem}.quick-grid,.metric-grid{gap:.42rem}.mini-stat,.metric-grid span{padding:.58rem .48rem}}
</style>
""",
    unsafe_allow_html=True,
)

market_service = MarketService()
portfolio_service = PortfolioService()
news_service = NewsService()
default_state = {"portfolio": portfolio_service.empty(), "last_portfolio_sync": None, "binance_connection_status": "not_configured", "binance_connection_message": "Connexion Binance non configurée.", "watchlist": ["bitcoin", "ethereum", "solana"], "screen": "Accueil", "currency": "USD", "theme": "Premium Dark", "refresh_interval": "90 secondes"}
for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Synchronisation automatique du portefeuille Binance en lecture seule.
previous_connection_status = st.session_state.binance_connection_status
try:
    sync_result = portfolio_service.sync_binance_portfolio()
except AttributeError:
    sync_result = portfolio_service.sync_portfolio()
except Exception:
    sync_result = portfolio_service._sync_error("not_configured", "Connexion Binance non configurée.")
st.session_state.binance_connection_status = sync_result.connection_status
st.session_state.binance_connection_message = sync_result.message
if sync_result.synced_at:
    st.session_state.last_portfolio_sync = sync_result.synced_at
if sync_result.connection_status == "connected":
    st.session_state.portfolio = sync_result.portfolio
elif sync_result.connection_status == "not_configured" and previous_connection_status != "imported_csv":
    st.session_state.portfolio = portfolio_service.empty()

with st.sidebar:
    st.header("Studio de données")
    uploaded = st.file_uploader("Importer un CSV Spot", type=["csv"], help="Import éducatif uniquement. Aucune clé API ni exécution.")
    if uploaded is not None:
        try:
            imported = portfolio_service.import_csv(uploaded)
            if st.button("Utiliser le portefeuille importé", type="primary", use_container_width=True):
                st.session_state.portfolio = imported
                st.session_state.binance_connection_status = "imported_csv"
                st.session_state.binance_connection_message = "Portefeuille importé depuis un CSV"
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
        coin_ids.extend(market_service.trending_ids())
    except Exception:
        st.sidebar.warning("Les tendances CoinGecko sont momentanément indisponibles.")
coin_ids = list(dict.fromkeys(coin_ids))

try:
    if refresh:
        market_service.clear_cache()
    market_df = market_service.prices(tuple(coin_ids), st.session_state.currency)
except Exception:
    st.warning("Les données CoinGecko sont momentanément indisponibles. Réessaie dans quelques instants.")
    st.stop()
if market_df.empty:
    st.warning("Ajoute des IDs CoinGecko valides pour commencer."); st.stop()

market_objects = market_service.market_objects(market_df)
market_lookup = market_service.market_lookup(market_objects)
market_ids = [coin.coin_id for coin in market_objects]
st.session_state.portfolio = portfolio_service.load(st.session_state.portfolio)
portfolio_data = portfolio_service.build_data(st.session_state.portfolio, market_objects, market_lookup)
portfolio = portfolio_data.holdings
total_value = portfolio_data.total_value
total_pnl = portfolio_data.total_pnl
total_pnl_pct = portfolio_data.total_pnl_pct
daily_pnl = portfolio_data.daily_pnl
daily_pnl_pct = portfolio_data.daily_pnl_pct
fav_ids = portfolio_data.favorite_ids
best_row = portfolio_data.best_row
worst_row = portfolio_data.worst_row

st.markdown(f"<div class='app-shell'><div class='topbar'><span class='icon-btn'>☰</span><div class='brand'>{html.escape(APP_NAME)}</div><div class='nav-icons'><span class='icon-btn'>🔔</span><span class='icon-btn'>👤</span></div></div></div>", unsafe_allow_html=True)
screen = st.radio("Navigation", SECTIONS, horizontal=True, label_visibility="collapsed", key="screen")
fng_value, fng_label = market_service.fear_greed()
dominance = market_service.btc_dominance(market_objects)
segments = portfolio_service.segment_allocation(total_value)
fng_display = f"{fng_value}/100" if fng_value is not None else "Indisponible"


SCREEN_RENDERERS = {
    "Accueil": lambda: render_home(
        best_row=best_row,
        worst_row=worst_row,
        portfolio=portfolio,
        market_lookup=market_lookup,
        market_objects=market_objects,
        total_value=total_value,
        daily_pnl=daily_pnl,
        daily_pnl_pct=daily_pnl_pct,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        dominance=dominance,
        fng_display=fng_display,
        fng_label=fng_label,
        pct_class=pct_class,
        sparkline_svg=sparkline_svg,
        binance_configured=portfolio_service.binance_configured,
        connection_status=st.session_state.binance_connection_status,
        connection_message=st.session_state.binance_connection_message,
    ),
    "Marchés": lambda: render_markets(
        market_objects=market_objects,
        fng_display=fng_display,
        dominance=dominance,
        render_market_card=render_market_card,
    ),
    "Portefeuille": lambda: render_portfolio(
        portfolio=portfolio,
        total_value=total_value,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        market_ids=market_ids,
        market_lookup=market_lookup,
        pct_class=pct_class,
        render_holding_card=render_holding_card,
        portfolio_service=portfolio_service,
        connection_status=st.session_state.binance_connection_status,
        connection_message=st.session_state.binance_connection_message,
        last_sync=st.session_state.last_portfolio_sync,
    ),
    "Bots": render_bots,
    "Actualités": lambda: render_news(
        news_service=news_service,
        one_sentence_summary=one_sentence_summary,
    ),
    "Calculateur": lambda: render_calculator(pct_class=pct_class),
    "Opportunités": lambda: render_opportunities(
        market_objects=market_objects,
        portfolio=portfolio,
        confidence_for=confidence_for,
        coin_logo=coin_logo,
        score_badge=score_badge,
        signal_label=signal_label,
    ),
    "Trader IA": lambda: render_trader_ai(market_objects=market_objects, portfolio=portfolio),
}

SCREEN_RENDERERS[screen]()
