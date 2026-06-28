from __future__ import annotations
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
        st.markdown(f"<div class='card'><span class='pill soft'>{article.source}</span><h3>{article.title}</h3><p class='muted'>{summary}</p></div>", unsafe_allow_html=True)
