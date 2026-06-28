from __future__ import annotations

import streamlit as st

from utils.constants import APP_SUBTITLE, FOOTER_TEXT


def render_footer() -> None:
    st.markdown(
        f"<div class='app-footer'><b>{FOOTER_TEXT}</b><span>{APP_SUBTITLE}</span></div>",
        unsafe_allow_html=True,
    )
