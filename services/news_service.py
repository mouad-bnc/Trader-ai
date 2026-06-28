from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass(slots=True)
class NewsArticle:
    title: str
    source: str
    url: str = ""
    description: str = ""
    image_url: str = ""
    published_at: str = ""
    ai_summary: str = ""


class NewsService:
    def __init__(self, timeout: int = 8) -> None:
        self.timeout = timeout

    def latest(self, query: str = "crypto") -> list[NewsArticle]:
        articles = self._coindesk()
        if articles:
            return articles
        return self._rss_fallback(query)

    def summarize(self, article: NewsArticle) -> str:
        text = article.description or article.title
        sentence = text.replace("\n", " ").split(". ")[0].strip()
        return sentence[:160] + ("…" if len(sentence) > 160 else "")

    def _coindesk(self) -> list[NewsArticle]:
        try:
            response = requests.get("https://data-api.coindesk.com/news/v1/article/list", params={"lang": "EN", "limit": 8}, timeout=self.timeout)
            response.raise_for_status()
            data = response.json().get("Data", [])
        except Exception:
            return []
        return [NewsArticle(title=str(item.get("TITLE", "Actualité crypto")), source=str(item.get("SOURCE_DATA", {}).get("NAME", "CoinDesk")), url=str(item.get("URL", "")), description=str(item.get("BODY", "")), image_url=str(item.get("IMAGE_URL", "")), published_at=str(item.get("PUBLISHED_ON", ""))) for item in data if isinstance(item, dict)]

    def _rss_fallback(self, query: str) -> list[NewsArticle]:
        return [NewsArticle(title="Actualités indisponibles", source="Mouad Capital AI", description=f"Impossible de charger les fournisseurs pour {query}. Réessayez plus tard.", ai_summary="Les marchés restent consultables et l'application continue de fonctionner hors ligne.")]
