from __future__ import annotations

import streamlit as st
from utils.constants import NAV_ITEMS


def selected_page() -> str:
    query = st.query_params.get("page", NAV_ITEMS[0])
    return query if query in NAV_ITEMS else NAV_ITEMS[0]
