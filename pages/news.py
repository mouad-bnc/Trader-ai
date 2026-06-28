from __future__ import annotations
import html
import streamlit as st
from components.cards import empty_state
from services.news_service import NewsService


def render(services: dict[str, object]) -> None:
    ns = services["news"]
    assert isinstance(ns, NewsService)
    st.title("Actualités")
    articles = ns.latest()
    if not articles:
        empty_state("Aucune actualité", "Les fournisseurs news sont indisponibles.")
    for article in articles:
        summary = article.ai_summary or ns.summarize(article)
        st.markdown(f"<div class='card'><span class='pill soft'>{html.escape(article.source)}</span><h3>{html.escape(article.title)}</h3><p class='muted'>{html.escape(summary)}</p></div>", unsafe_allow_html=True)
