from __future__ import annotations

import streamlit as st
from utils.constants import APP_NAME, APP_SUBTITLE
from utils.helpers import now_casablanca_label

__all__ = ["render_header"]


_LOGO_SVG = """
<svg class='brand-logo' viewBox='0 0 40 40' role='img' aria-label='MSH AI-Invest logo' xmlns='http://www.w3.org/2000/svg'>
  <defs>
    <linearGradient id='coinGold' x1='8' x2='34' y1='5' y2='35' gradientUnits='userSpaceOnUse'>
      <stop stop-color='#FFE8A3'/>
      <stop offset='.5' stop-color='#D4AF37'/>
      <stop offset='1' stop-color='#8D6E18'/>
    </linearGradient>
  </defs>
  <circle cx='28' cy='12' r='7.5' fill='url(#coinGold)' stroke='rgba(255,255,255,.35)' stroke-width='1.2'/>
  <text x='28' y='15.2' text-anchor='middle' font-size='9' font-weight='900' fill='#090909'>$</text>
  <path d='M20 31V19' stroke='#D4AF37' stroke-width='2.6' stroke-linecap='round'/>
  <path d='M20 22C14.2 21.8 10.8 18.7 9.6 13.2C15.4 13.1 19 16.1 20 22Z' fill='#2ECC71' stroke='rgba(255,255,255,.22)' stroke-width='1'/>
  <path d='M21 20C24.6 18.2 28.1 18.9 31 22.5C26.7 24.8 23.2 24 21 20Z' fill='#D4AF37' stroke='rgba(255,255,255,.22)' stroke-width='1'/>
  <path d='M13 32.5H27' stroke='#D4AF37' stroke-width='2.4' stroke-linecap='round'/>
</svg>
"""


def render_header() -> None:
    st.markdown(
        f"""
        <div class='topbar'>
            <div class='brand'>
                <div class='brand-identity'>{_LOGO_SVG}<div><span>{APP_NAME}</span><small>{APP_SUBTITLE}</small></div></div>
                <div class='market-time'>{now_casablanca_label()}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
