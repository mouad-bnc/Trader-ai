from __future__ import annotations

import streamlit as st
from utils.constants import APP_NAME, APP_VERSION
from utils.helpers import now_utc_label


def render_header(active: str, items: list[str]) -> None:
    links = "".join(f"<a class='{ 'active' if item == active else '' }' href='?page={item}'>{item}</a>" for item in items)
    st.markdown(f"<div class='topbar'><div class='brand'><span><b>✦</b> {APP_NAME}</span><small>v{APP_VERSION}</small></div><div class='nav'>{links}</div><div class='muted'>{now_utc_label()}</div></div>", unsafe_allow_html=True)
