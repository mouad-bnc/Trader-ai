from __future__ import annotations

import html

import streamlit as st

from components.ui import render_empty_card


def render_news(*, news_service, one_sentence_summary) -> None:
    try: articles = news_service.latest(per_page=10) or news_service.empty_news()
    except Exception: articles = news_service.empty_news()
    if not articles:
        render_empty_card("▧", "Feed indisponible", "Aucune actualité vérifiée n'est disponible pour le moment. Réessayez après la prochaine synchronisation.")
    for article in articles[:10]:
        tags = article.get('tags') or [tag for tag in ['BTC','ETH','SOL','DOGE','SUI'] if tag.lower() in str(article).lower()] or ['Crypto']
        image = html.escape(str(article.get('image') or ''))
        image_style = f" style=\"background-image:url('{image}')\"" if image else ""
        source = html.escape(str(article.get('source') or 'Source crypto'))
        st.markdown(f"<article class='news-card'><div class='news-img'{image_style}></div><span class='eyebrow'>{source}</span><h3>{html.escape(str(article.get('title') or 'Actualité crypto'))}</h3><p class='muted'>{html.escape(str(article.get('date') or article.get('created_at') or 'Maintenant'))}</p><p>{html.escape(one_sentence_summary(article))}</p><div class='badge-row'>{''.join(f'<em>{html.escape(str(t))}</em>' for t in tags)}</div></article>", unsafe_allow_html=True)
