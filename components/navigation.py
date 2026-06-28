from __future__ import annotations

import streamlit as st
from utils.constants import NAV_ITEMS

NAV_STATE_KEY = "selected_page"


def selected_page() -> str:
    """Render the top navigation and return the selected page."""
    current_page = st.session_state.get(NAV_STATE_KEY, NAV_ITEMS[0])
    if current_page not in NAV_ITEMS:
        current_page = NAV_ITEMS[0]
        st.session_state[NAV_STATE_KEY] = current_page

    selected = st.segmented_control(
        label="Navigation",
        options=NAV_ITEMS,
        selection_mode="single",
        default=current_page,
        key=NAV_STATE_KEY,
        label_visibility="collapsed",
    )

    if not isinstance(selected, str) or selected not in NAV_ITEMS:
        st.session_state[NAV_STATE_KEY] = NAV_ITEMS[0]
        return NAV_ITEMS[0]

    return selected
