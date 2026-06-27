"""CoinGecko-only market data client for Trader AI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import requests

BASE_URL = "https://api.coingecko.com/api/v3"
DEFAULT_COINS = ["bitcoin", "ethereum", "solana", "chainlink", "cardano", "sui", "dogecoin", "render-token"]


@dataclass(frozen=True)
class MarketCoin:
    """Normalized CoinGecko market row used by the UI and analytics layer."""

    coin_id: str
    symbol: str
    name: str
    image: str
    current_price: float
    market_cap: float
    market_cap_rank: int | None
    total_volume: float
    price_change_24h_pct: float
    price_change_7d_pct: float
    price_change_30d_pct: float
    high_24h: float
    low_24h: float
    ath_change_pct: float
    sparkline: list[float]


class CoinGeckoClient:
    """Small resilient wrapper around public CoinGecko endpoints.

    The app intentionally uses no API keys and no exchange APIs. If CoinGecko is
    unavailable, callers receive a clear RuntimeError that can be rendered in the UI.
    """

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "TraderAI/0.1"})

    def _get(self, path: str, params: dict[str, object] | None = None) -> object:
        try:
            response = self.session.get(f"{BASE_URL}{path}", params=params, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"CoinGecko request failed: {exc}") from exc
        return response.json()

    def fetch_markets(self, coin_ids: Iterable[str], currency: str = "usd") -> list[MarketCoin]:
        ids = [coin_id.strip().lower() for coin_id in coin_ids if coin_id.strip()]
        if not ids:
            return []

        data = self._get(
            "/coins/markets",
            {
                "vs_currency": currency.lower(),
                "ids": ",".join(dict.fromkeys(ids)),
                "order": "market_cap_desc",
                "per_page": min(250, len(ids)),
                "page": 1,
                "sparkline": "true",
                "price_change_percentage": "24h,7d,30d",
                "locale": "en",
            },
        )
        if not isinstance(data, list):
            raise RuntimeError("CoinGecko returned an unexpected market payload.")
        return [self._parse_market_coin(item) for item in data]


    def fetch_news(self, per_page: int = 10, coin_id: str | None = None) -> list[dict[str, object]]:
        """Fetch latest CoinGecko news when the public endpoint is available."""

        params: dict[str, object] = {"per_page": max(1, min(20, per_page)), "page": 1}
        if coin_id:
            params["coin_id"] = coin_id
        data = self._get("/news", params)
        if isinstance(data, dict):
            articles = data.get("data") or data.get("news") or data.get("articles") or []
        else:
            articles = data if isinstance(data, list) else []
        return [item for item in articles if isinstance(item, dict)]

    def trending_ids(self, limit: int = 7) -> list[str]:
        data = self._get("/search/trending")
        if not isinstance(data, dict):
            return []
        coins = data.get("coins", [])
        ids: list[str] = []
        for item in coins[:limit]:
            coin = item.get("item", {}) if isinstance(item, dict) else {}
            coin_id = coin.get("id")
            if isinstance(coin_id, str):
                ids.append(coin_id)
        return ids

    @staticmethod
    def _parse_market_coin(item: dict[str, object]) -> MarketCoin:
        sparkline_payload = item.get("sparkline_in_7d") or {}
        sparkline = sparkline_payload.get("price", []) if isinstance(sparkline_payload, dict) else []
        return MarketCoin(
            coin_id=str(item.get("id", "")),
            symbol=str(item.get("symbol", "")).upper(),
            name=str(item.get("name", "")),
            image=str(item.get("image", "")),
            current_price=float(item.get("current_price") or 0),
            market_cap=float(item.get("market_cap") or 0),
            market_cap_rank=item.get("market_cap_rank") if isinstance(item.get("market_cap_rank"), int) else None,
            total_volume=float(item.get("total_volume") or 0),
            price_change_24h_pct=float(item.get("price_change_percentage_24h_in_currency") or 0),
            price_change_7d_pct=float(item.get("price_change_percentage_7d_in_currency") or 0),
            price_change_30d_pct=float(item.get("price_change_percentage_30d_in_currency") or 0),
            high_24h=float(item.get("high_24h") or 0),
            low_24h=float(item.get("low_24h") or 0),
            ath_change_pct=float(item.get("ath_change_percentage") or 0),
            sparkline=[float(value) for value in sparkline if isinstance(value, int | float)],
        )


def markets_to_frame(markets: list[MarketCoin]) -> pd.DataFrame:
    """Convert market objects to a DataFrame for Streamlit tables."""

    return pd.DataFrame([coin.__dict__ for coin in markets])
