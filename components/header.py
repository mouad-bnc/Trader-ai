from __future__ import annotations

import html

import streamlit as st
from utils.constants import APP_NAME, APP_SUBTITLE, APP_VERSION
from utils.helpers import now_utc_label


def render_header(active: str, items: list[str]) -> None:
    links = "".join(f"<a class='{ 'active' if item == active else '' }' href='?page={html.escape(item, quote=True)}'>{html.escape(item)}</a>" for item in items)
    pillar_logo = """
    <span class='brand-logo' aria-label='Pillar Gold logo'>
        <svg viewBox='0 0 48 48' role='img' aria-hidden='true' focusable='false'>
            <defs><linearGradient id='pillar-gold' x1='10' y1='6' x2='38' y2='42' gradientUnits='userSpaceOnUse'><stop stop-color='#FFE29A'/><stop offset='.55' stop-color='#F3BA2F'/><stop offset='1' stop-color='#C99400'/></linearGradient></defs>
            <path class='pillar-cap' d='M24 6 8 14v4h32v-4L24 6Z'/>
            <path class='pillar-body' d='M12 21h6v15h-6V21Zm9 0h6v15h-6V21Zm9 0h6v15h-6V21Z'/>
            <path class='pillar-base' d='M9 38h30v4H9v-4Z'/>
        </svg>
    </span>
    """
    st.markdown(
        f"<div class='topbar'><div class='brand'><span>{pillar_logo} {html.escape(APP_NAME)}</span>"
        f"<small>{html.escape(APP_SUBTITLE)} · v{html.escape(APP_VERSION)}</small></div>"
        f"<div class='nav'>{links}</div><div class='muted'>{now_utc_label()}</div></div>",
        unsafe_allow_html=True,
    )
