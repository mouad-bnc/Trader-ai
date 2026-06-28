from __future__ import annotations
import streamlit as st
from utils.helpers import money


def render(services: dict[str, object]) -> None:
    st.title("Calculateur")
    capital = st.number_input("Capital", min_value=0.0, value=1000.0, step=50.0)
    entry = st.number_input("Prix d'entrée", min_value=0.0, value=100.0, step=1.0)
    target = st.number_input("Objectif", min_value=0.0, value=120.0, step=1.0)
    stop = st.number_input("Stop", min_value=0.0, value=90.0, step=1.0)
    qty = capital / entry if entry else 0
    gain = (target - entry) * qty
    risk = (entry - stop) * qty
    ratio = gain / risk if risk > 0 else 0
    st.markdown(f"<div class='card'><div class='metric'><div><span class='muted'>Quantité</span><b>{qty:.6f}</b></div><div><span class='muted'>Gain potentiel</span><b>{money(gain)}</b></div><div><span class='muted'>R/R</span><b>{ratio:.2f}</b></div></div></div>", unsafe_allow_html=True)
