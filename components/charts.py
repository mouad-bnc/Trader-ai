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


def allocation_pie(data: dict[str, float]) -> None:
    colors = [GOLD, "#F3D675", "#B88A1D", "#2ECC71", "#3498DB", "#9B59B6", "#E67E22"]
    items = [(k, max(0.0, min(100.0, float(v)))) for k, v in data.items() if v > 0]
    if not items:
        st.markdown("<div class='card'><h3>Allocation pie chart</h3><p class='muted'>Aucune allocation disponible.</p></div>", unsafe_allow_html=True)
        return
    offset = 25.0
    circles = []
    legend = []
    for index, (label, value) in enumerate(items[:7]):
        color = colors[index % len(colors)]
        circles.append(f"<circle r='15.9' cx='18' cy='18' fill='transparent' stroke='{color}' stroke-width='8' stroke-dasharray='{value:.2f} {100-value:.2f}' stroke-dashoffset='-{offset:.2f}'></circle>")
        offset += value
        legend.append(f"<p class='row'><span><i style='display:inline-block;width:10px;height:10px;border-radius:50%;background:{color};margin-right:8px'></i>{html.escape(label)}</span><b>{value:.1f}%</b></p>")
    svg = "<svg viewBox='0 0 36 36' style='width:190px;max-width:100%;transform:rotate(-90deg)'>" + "".join(circles) + "</svg>"
    st.markdown(f"<div class='card'><h3>Allocation pie chart</h3><div class='row' style='align-items:center;flex-wrap:wrap'>{svg}<div style='flex:1;min-width:180px'>{''.join(legend)}</div></div></div>", unsafe_allow_html=True)


def range_chart(title: str, values: list[float], range_label: str) -> None:
    if len(values) < 2:
        st.markdown(f"<div class='card empty'><span class='pill soft'>{html.escape(range_label)}</span><h3>{html.escape(title)}</h3><p class='muted'>Données insuffisantes pour afficher ce graphique.</p></div>", unsafe_allow_html=True)
        return
    positive = values[-1] >= values[0]
    st.markdown(f"<div class='card compact-chart compact-card'><div class='row'><h3>{html.escape(title)}</h3><span class='pill soft'>{html.escape(range_label)}</span></div>{sparkline(values, positive)}</div>", unsafe_allow_html=True)
