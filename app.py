from __future__ import annotations

import pandas as pd
import streamlit as st

from trader_assistant import DEFAULT_SYMBOLS, analyze_symbol, fmt_price

st.set_page_config(page_title="Trader AI v1", page_icon="📈", layout="wide")

st.title("📈 Trader AI v1")
st.caption("Analyse crypto éducative basée sur données publiques Binance Spot. Aucun ordre n'est envoyé.")

with st.sidebar:
    st.header("Paramètres")
    symbols_text = st.text_input("Cryptos à analyser", " ".join(DEFAULT_SYMBOLS))
    budget = st.number_input("Budget USDT à analyser", min_value=10.0, max_value=100000.0, value=100.0, step=10.0)
    run = st.button("Analyser maintenant", type="primary")

symbols = [s.strip().upper() for s in symbols_text.replace(",", " ").split() if s.strip()]

if not symbols:
    st.warning("Ajoute au moins une paire, exemple : BTCUSDT SOLUSDT SUIUSDT DOGEUSDT")
    st.stop()

if run or "signals" not in st.session_state:
    signals = []
    errors = []
    progress = st.progress(0, text="Récupération des données...")
    for i, symbol in enumerate(symbols, start=1):
        try:
            signals.append(analyze_symbol(symbol))
        except Exception as exc:
            errors.append(f"{symbol}: {exc}")
        progress.progress(i / len(symbols), text=f"Analyse {symbol}...")
    progress.empty()
    st.session_state["signals"] = signals
    st.session_state["errors"] = errors
else:
    signals = st.session_state["signals"]
    errors = st.session_state.get("errors", [])

if errors:
    with st.expander("Erreurs de récupération"):
        for err in errors:
            st.error(err)

if not signals:
    st.error("Aucune donnée récupérée.")
    st.stop()

ranked = sorted(signals, key=lambda s: s.opportunity_score, reverse=True)
best = ranked[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Meilleure opportunité", best.symbol)
col2.metric("Score", f"{best.opportunity_score}/10")
col3.metric("Décision", best.decision)
if best.opportunity_score >= 8:
    allocation = budget * 0.40
elif best.opportunity_score >= 6:
    allocation = budget * 0.20
else:
    allocation = 0.0
col4.metric("Allocation prudente", f"{allocation:.2f} USDT")

st.divider()

rows = []
for s in ranked:
    rows.append({
        "Crypto": s.symbol,
        "Prix USDT": fmt_price(s.price),
        "24h": f"{s.change_24h_pct:+.2f}%",
        "RSI 14j": f"{s.rsi_14:.1f}",
        "SMA 20j": fmt_price(s.sma_20),
        "Distance SMA": f"{s.distance_to_sma_pct:+.2f}%",
        "Volatilité 20j": f"{s.volatility_20d_pct:.2f}%",
        "Score": s.opportunity_score,
        "Décision": s.decision,
        "Zone achat": f"{fmt_price(s.suggested_buy_zone[0])} - {fmt_price(s.suggested_buy_zone[1])}",
        "Stop indicatif": fmt_price(s.risk_stop),
        "Note": s.note,
    })

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, hide_index=True)

st.subheader("Lecture Trader")
if best.opportunity_score >= 8:
    st.success(f"Signal intéressant sur {best.symbol}. Renforcer léger peut être envisagé, maximum {allocation:.2f} USDT sur ton budget analysé.")
elif best.opportunity_score >= 6:
    st.info(f"Signal moyen sur {best.symbol}. Petit achat possible, mais pas d'entrée agressive.")
else:
    st.warning("Aucune opportunité forte. Le plus prudent est de garder les USDT et attendre une meilleure zone.")

st.caption("Important : ceci n'est pas un conseil financier. L'outil aide à structurer l'analyse, pas à garantir un résultat.")
