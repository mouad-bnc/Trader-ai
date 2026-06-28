from __future__ import annotations
import streamlit as st


def render(services: dict[str, object]) -> None:
    st.title("Bots")
    st.markdown("<div class='card'><span class='pill'>Simulation only</span><h3>Bots d'observation</h3><p class='muted'>Surveillance DCA, momentum et alertes. Aucune exécution d'ordre, aucun trading automatique.</p><div class='metric'><div><span class='muted'>DCA</span><b>Actif</b></div><div><span class='muted'>Risque</span><b>Bas</b></div><div><span class='muted'>Ordres</span><b>0</b></div></div></div>", unsafe_allow_html=True)
