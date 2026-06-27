from __future__ import annotations

import html

import streamlit as st


def render_empty_card(icon: str, title: str, description: str, *, section_head: bool = False, badge: str | None = None) -> None:
    if section_head and badge is not None:
        st.markdown(
            f"<section class='empty-card'><div class='section-head'><h3>{html.escape(title)}</h3><span class='pill'>{html.escape(badge)}</span></div><p class='muted'>{html.escape(description)}</p></section>",
            unsafe_allow_html=True,
        )
        return
    st.markdown(
        f"<section class='empty-card'><div class='empty-icon'>{html.escape(icon)}</div><h2>{html.escape(title)}</h2><p class='muted'>{html.escape(description)}</p></section>",
        unsafe_allow_html=True,
    )


def render_section_card(title: str, subtitle: str = "", *, notice: bool = False) -> None:
    paragraph_class = "notice" if notice else "muted"
    subtitle_html = f"<p class='{paragraph_class}'>{html.escape(subtitle)}</p>" if subtitle else ""
    st.markdown(f"<section class='glass-card'><h2>{html.escape(title)}</h2>{subtitle_html}</section>", unsafe_allow_html=True)


def render_section_head_card(title: str, detail: str) -> None:
    st.markdown(
        f"<section class='glass-card'><div class='section-head'><h2>{html.escape(title)}</h2><span class='muted'>{html.escape(detail)}</span></div></section>",
        unsafe_allow_html=True,
    )


def _class_attr(css_class: str | None) -> str:
    return f" class='{html.escape(css_class)}'" if css_class else ""


def render_metric_grid_card(metrics: list[tuple[str, str, str | None]], *, grid_class: str = "metric-grid") -> None:
    cells = "".join(
        f"<span>{html.escape(label)} <b{_class_attr(css_class)}>{value}</b></span>"
        for label, value, css_class in metrics
    )
    st.markdown(f"<section class='glass-card'><div class='{html.escape(grid_class)}'>{cells}</div></section>", unsafe_allow_html=True)
