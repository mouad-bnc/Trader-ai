from __future__ import annotations

import html

import streamlit as st


def render_news(*, client, demo_news, one_sentence_summary) -> None:
    @st.cache_data(ttl=300, show_spinner=False)
    def load_news() -> list[dict[str, object]]: return client.fetch_news(per_page=10)
    try: articles = load_news() or demo_news()
    except Exception: articles = demo_news()
    if not articles:
        st.markdown("<section class='empty-card'><div class='empty-icon'>▧</div><h2>Feed indisponible</h2><p class='muted'>Aucune actualité vérifiée n'est disponible pour le moment. Réessayez après la prochaine synchronisation.</p></section>", unsafe_allow_html=True)
    for article in articles[:10]:
        tags = article.get('tags') or [tag for tag in ['BTC','ETH','SOL','DOGE','SUI'] if tag.lower() in str(article).lower()] or ['Crypto']
        image = html.escape(str(article.get('thumb_2x') or article.get('image') or article.get('urlToImage') or ''))
        image_style = f" style=\"background-image:url('{image}')\"" if image else ""
        source = html.escape(str(article.get('source') or article.get('source_name') or 'Source crypto'))
        st.markdown(f"<article class='news-card'><div class='news-img'{image_style}></div><span class='eyebrow'>{source}</span><h3>{html.escape(str(article.get('title') or 'Actualité crypto'))}</h3><p class='muted'>{html.escape(str(article.get('date') or article.get('created_at') or 'Maintenant'))}</p><p>{html.escape(one_sentence_summary(article))}</p><div class='badge-row'>{''.join(f'<em>{html.escape(str(t))}</em>' for t in tags)}</div></article>", unsafe_allow_html=True)
