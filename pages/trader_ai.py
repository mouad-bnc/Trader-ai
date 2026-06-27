from __future__ import annotations

import html

import streamlit as st

from portfolio_analytics import recommendation_for


def render_trader_ai(*, market_objects, portfolio, **_ignored_kwargs) -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "bot", "text": "Bonjour Mouad 👋\n\nJe suis Trader.\n\nJe peux analyser :\n• ton portefeuille\n• le marché\n• une crypto\n• les news\n• les opportunités."}]
    for msg in st.session_state.messages:
        st.markdown(f"<div class='chat-bubble {'bot' if msg['role']=='bot' else 'user'}'>{html.escape(msg['text'])}</div>", unsafe_allow_html=True)
    prompt = st.text_input("Message", placeholder="Demandez à Trader d’analyser votre portefeuille...")
    for suggestion in ["Analyser mon portefeuille", "Faut-il acheter SOL ?", "DOGE est-il encore intéressant ?", "Meilleure opportunité aujourd’hui", "Calculer mon prix moyen"]:
        if st.button(suggestion, use_container_width=True): prompt = suggestion
    if prompt:
        st.session_state.messages.append({"role":"user","text":prompt})
        if not market_objects:
            st.session_state.messages.append({"role":"bot","text":"Les données marché sont indisponibles pour le moment."})
        else:
            best = max(market_objects, key=lambda c: recommendation_for(c).opportunity_score)
            synced_count = len(portfolio) if portfolio is not None else 0
            st.session_state.messages.append({"role":"bot","text":f"Analyse indicative basée sur ton portefeuille synchronisé ({synced_count} actif(s)) : {best.name} obtient le meilleur score actuel ({recommendation_for(best).opportunity_score}/100). Vérifie toujours ton risque, ton prix moyen et ton stop avant toute décision."})
        st.rerun()
