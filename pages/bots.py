from __future__ import annotations

import streamlit as st


def render_bots() -> None:
    st.markdown("<section class='empty-card'><div class='empty-icon'>⌘</div><h2>Bots</h2><p class='muted'>Aucun bot connecté. Les performances réelles s'afficheront uniquement après connexion d'une source de données.</p></section>", unsafe_allow_html=True)
