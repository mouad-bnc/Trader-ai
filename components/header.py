from __future__ import annotations

import streamlit as st
from utils.constants import APP_NAME, APP_SUBTITLE, APP_VERSION
from utils.helpers import now_utc_label


def render_header() -> None:
    st.markdown(
        f"<div class='topbar'><div class='brand'><span><b>✦</b> {APP_NAME}</span>"
        f"<small>{APP_SUBTITLE} · v{APP_VERSION}</small></div>"
        f"<div class='muted'>{now_utc_label()}</div></div>",
        unsafe_allow_html=True,
    )
