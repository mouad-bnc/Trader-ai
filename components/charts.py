from __future__ import annotations

import html
import math

import streamlit as st
from utils.constants import GOLD, GREEN, RED


def sparkline(values: list[float] | None, positive: bool = True) -> str:
    pts = [float(v) for v in values or [] if math.isfinite(float(v))]
    if len(pts) < 2:
        pts = [1, 1.02, .99, 1.04, 1.03, 1.06]
    low, high = min(pts), max(pts)
    spread = high - low or 1
    coords = [f"{i*160/(len(pts)-1):.1f},{58-((v-low)/spread*48):.1f}" for i, v in enumerate(pts)]
    color = GREEN if positive else RED
    return f"<svg class='spark' viewBox='0 0 160 64' preserveAspectRatio='none'><polyline points='{html.escape(' '.join(coords))}' fill='none' stroke='{color}' stroke-width='3.5' stroke-linecap='round'/></svg>"


def allocation_bar(data: dict[str, float]) -> None:
    rows = "".join(f"<p class='row'><span>{html.escape(k)}</span><b>{v:.1f}%</b></p><div style='height:8px;background:rgba(255,255,255,.08);border-radius:99px;overflow:hidden'><i style='display:block;width:{max(0,min(100,v))}%;height:100%;background:{GOLD};border-radius:99px'></i></div>" for k, v in data.items())
    st.markdown(f"<div class='card'><h3>Allocation</h3>{rows or '<p class=muted>Aucune allocation disponible.</p>'}</div>", unsafe_allow_html=True)
