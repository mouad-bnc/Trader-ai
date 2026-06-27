"""Service central des actualités crypto pour Trader."""

from __future__ import annotations

from typing import Protocol

import streamlit as st

from coingecko import CoinGeckoClient


class NewsProvider(Protocol):
    def fetch_news(self, per_page: int = 10, coin_id: str | None = None) -> list[dict[str, object]]: ...


class NewsService:
    """Agrège plusieurs fournisseurs et renvoie un format d'article uniforme."""

    def __init__(self, providers: list[NewsProvider] | None = None) -> None:
        self.providers = providers or [CoinGeckoClient()]

    def latest(self, per_page: int = 10) -> list[dict[str, object]]:
        return _cached_latest_news(per_page)

    @staticmethod
    def normalize(article: dict[str, object]) -> dict[str, object]:
        tags = article.get("tags") or [tag for tag in ["BTC", "ETH", "SOL", "DOGE", "SUI"] if tag.lower() in str(article).lower()] or ["Crypto"]
        return {
            "title": article.get("title") or "Actualité crypto",
            "description": article.get("description") or article.get("summary") or article.get("title") or "Dernière actualité du marché crypto.",
            "date": article.get("date") or article.get("created_at") or "Maintenant",
            "source": article.get("source") or article.get("source_name") or "Source crypto",
            "image": article.get("thumb_2x") or article.get("image") or article.get("urlToImage") or "",
            "tags": tags,
            "url": article.get("url") or article.get("link") or "",
        }

    @staticmethod
    def empty_news() -> list[dict[str, object]]:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def _cached_latest_news(per_page: int = 10) -> list[dict[str, object]]:
    service = NewsService(providers=[CoinGeckoClient()])
    for provider in service.providers:
        try:
            articles = provider.fetch_news(per_page=per_page)
            normalized = [service.normalize(article) for article in articles if isinstance(article, dict)]
            if normalized:
                return normalized[:per_page]
        except Exception:
            continue
    return []


__all__ = ["NewsService"]
