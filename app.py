import json
import time
from datetime import datetime, timezone

import requests
import streamlit as st

st.set_page_config(
    page_title="Trader AI V4",
    page_icon="📈",
    layout="wide",
)

COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"

DEFAULT_CONFIG = {
    "watchlist": ["bitcoin", "solana", "sui", "dogecoin"],
    "refresh_seconds": 60,
    "default_budget_usdt": 100,
}


def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return {**DEFAULT_CONFIG, **cfg}
    except Exception:
        return DEFAULT_CONFIG


@st.cache_data(ttl=60)
def fetch_markets(coin_ids):
    params = {
        "vs_currency": "usd",
        "ids": ",".join(coin_ids),
        "order": "market_cap_desc",
        "per_page": len(coin_ids),
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h,7d",
    }
    r = requests.get(COINGECKO_MARKETS_URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def score_coin(c):
    change_24h = c.get("price_change_percentage_24h") or 0
    change_7d = c.get("price_change_percentage_7d_in_currency") or 0
    volume = c.get("total_volume") or 0
    market_cap = c.get("market_cap") or 1
    volume_ratio = min(volume / market_cap, 0.20) / 0.20 * 20

    score = 50
    score += max(min(change_24h * 2, 20), -20)
    score += max(min(change_7d, 20), -20)
    score += volume_ratio - 10
    return max(0, min(100, round(score)))


def decision(score, change_24h):
    if score >= 75 and change_24h > -5:
        return "🟢 Opportunité forte", "Renforcer léger"
    if score >= 60:
        return "🟡 Opportunité moyenne", "Attendre / petit DCA"
    if score >= 45:
        return "⚪ Neutre", "Attendre"
    return "🔴 Risque élevé", "Ne rien faire"


def fmt_money(x):
    if x is None:
        return "-"
    if x >= 1000:
        return f"${x:,.0f}"
    return f"${x:,.4f}" if x < 1 else f"${x:,.2f}"


def fmt_pct(x):
    if x is None:
        return "-"
    sign = "+" if x >= 0 else ""
    return f"{sign}{x:.2f}%"


config = load_config()

st.title("📈 Trader AI V4")
st.caption("Assistant crypto personnel — données CoinGecko, aucune connexion Binance, aucun ordre exécuté.")

with st.sidebar:
    st.header("Paramètres")
    budget = st.number_input("Renfort prévu (USDT)", min_value=10, max_value=10000, value=int(config.get("default_budget_usdt", 100)), step=10)
    watchlist_text = st.text_area(
        "Watchlist CoinGecko IDs",
        value=", ".join(config.get("watchlist", [])),
        help="Exemples : bitcoin, solana, sui, dogecoin",
    )
    refresh = st.button("🔄 Actualiser")
    if refresh:
        st.cache_data.clear()

coin_ids = [x.strip().lower() for x in watchlist_text.split(",") if x.strip()]

try:
    data = fetch_markets(coin_ids)
except Exception as e:
    st.error(f"Erreur de récupération CoinGecko : {e}")
    st.stop()

updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
st.caption(f"Dernière mise à jour : {updated_at}")

if not data:
    st.warning("Aucune donnée trouvée. Vérifie les CoinGecko IDs dans la watchlist.")
    st.stop()

scores = [score_coin(c) for c in data]
market_score = round(sum(scores) / len(scores))

col1, col2, col3 = st.columns(3)
col1.metric("Score marché", f"{market_score}/100")
col2.metric("Budget renfort", f"{budget} USDT")
col3.metric("Actifs suivis", len(data))

st.subheader("🎯 Décision rapide")
best = max(data, key=score_coin)
best_score = score_coin(best)
best_status, best_action = decision(best_score, best.get("price_change_percentage_24h") or 0)

if best_score >= 70:
    st.success(f"Meilleure opportunité actuelle : **{best.get('symbol','').upper()}** — {best_status}. Action : **{best_action}**.")
elif best_score >= 55:
    st.info(f"Marché encore mitigé. Meilleur candidat : **{best.get('symbol','').upper()}** — {best_status}. Action : **{best_action}**.")
else:
    st.warning("Aucun signal fort pour investir maintenant. Priorité : attendre une meilleure zone.")

st.subheader("📊 Watchlist")

for c in data:
    score = score_coin(c)
    status, action = decision(score, c.get("price_change_percentage_24h") or 0)
    symbol = c.get("symbol", "").upper()
    name = c.get("name", symbol)
    price = c.get("current_price")
    change_24h = c.get("price_change_percentage_24h")
    change_7d = c.get("price_change_percentage_7d_in_currency")
    market_cap = c.get("market_cap")
    volume = c.get("total_volume")

    with st.container(border=True):
        a, b, c1, d, e = st.columns([1.5, 1.2, 1.1, 1.1, 1.4])
        a.markdown(f"### {symbol}\n{name}")
        b.metric("Prix", fmt_money(price), fmt_pct(change_24h))
        c1.metric("7 jours", fmt_pct(change_7d))
        d.metric("Score", f"{score}/100")
        e.markdown(f"**{status}**\n\nAction : **{action}**")

        st.progress(score / 100)
        qty = budget / price if price else 0
        st.caption(f"Avec {budget} USDT, quantité estimée : {qty:.6f} {symbol}. Market cap : {fmt_money(market_cap)} | Volume 24h : {fmt_money(volume)}")

st.subheader("🧠 Règles de prudence")
st.write(
    "Trader AI V4 sert à suivre le marché et structurer la décision. "
    "Il ne remplace pas ton jugement, et il n’exécute aucun ordre. "
    "Pour ton renfort de 100 USDT, l’idée reste d’acheter progressivement, pas de tout mettre sur un seul signal."
)
