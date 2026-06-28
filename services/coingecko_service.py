from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests

from utils.constants import DEFAULT_CURRENCY, DEFAULT_SYMBOLS
from utils.helpers import safe_float, safe_int


@dataclass(slots=True)
class MarketAsset:
    id: str
    symbol: str
    name: str
    image: str = ""
    current_price: float = 0.0
    market_cap: float = 0.0
    market_cap_rank: int = 0
    total_volume: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    price_change_24h_pct: float = 0.0
    price_change_7d_pct: float = 0.0
    sparkline: list[float] = field(default_factory=list)


@dataclass(slots=True)
class FearGreed:
    value: int | None = None
    label: str = "Indisponible"


class CoinGeckoService:
    def __init__(self, base_url: str = "https://api.coingecko.com/api/v3", timeout: int = 8) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            response = requests.get(f"{self.base_url}{path}", params=params or {}, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def get_markets(self, ids: list[str] | None = None, currency: str = DEFAULT_CURRENCY) -> list[MarketAsset]:
        payload = self._get("/coins/markets", {"vs_currency": currency, "ids": ",".join(ids or DEFAULT_SYMBOLS), "order": "market_cap_desc", "sparkline": "true", "price_change_percentage": "7d"})
        if not isinstance(payload, list):
            return []
        return [self._asset(item) for item in payload if isinstance(item, dict)]

    def trending(self) -> list[MarketAsset]:
        payload = self._get("/search/trending")
        coins = payload.get("coins", []) if isinstance(payload, dict) else []
        assets: list[MarketAsset] = []
        for entry in coins[:8]:
            item = entry.get("item", {}) if isinstance(entry, dict) else {}
            assets.append(MarketAsset(id=str(item.get("id", "")), symbol=str(item.get("symbol", "")).upper(), name=str(item.get("name", "Actif")), image=str(item.get("small", "")), market_cap_rank=safe_int(item.get("market_cap_rank"))))
        return assets

    def global_metrics(self) -> dict[str, float]:
        payload = self._get("/global")
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        dominance = data.get("market_cap_percentage", {}) if isinstance(data, dict) else {}
        return {"btc_dominance": safe_float(dominance.get("btc")), "market_cap_change_24h": safe_float(data.get("market_cap_change_percentage_24h_usd"))}

    def fear_greed(self) -> FearGreed:
        try:
            response = requests.get("https://api.alternative.me/fng/", params={"limit": 1, "format": "json"}, timeout=self.timeout)
            response.raise_for_status()
            data = (response.json().get("data") or [{}])[0]
            return FearGreed(value=safe_int(data.get("value")), label=str(data.get("value_classification") or "Marché"))
        except Exception:
            return FearGreed()

    def history(self, coin_id: str, days: int = 7, currency: str = DEFAULT_CURRENCY) -> list[float]:
        payload = self._get(f"/coins/{coin_id}/market_chart", {"vs_currency": currency, "days": days})
        prices = payload.get("prices", []) if isinstance(payload, dict) else []
        return [safe_float(row[1]) for row in prices if isinstance(row, list) and len(row) > 1]

    def top_gainers_losers(self, markets: list[MarketAsset]) -> tuple[list[MarketAsset], list[MarketAsset]]:
        ordered = sorted(markets, key=lambda asset: asset.price_change_24h_pct, reverse=True)
        return ordered[:3], list(reversed(ordered[-3:]))

    def _asset(self, item: dict[str, Any]) -> MarketAsset:
        spark = item.get("sparkline_in_7d", {}).get("price", []) if isinstance(item.get("sparkline_in_7d"), dict) else []
        return MarketAsset(id=str(item.get("id", "")), symbol=str(item.get("symbol", "")).upper(), name=str(item.get("name", "Actif")), image=str(item.get("image", "")), current_price=safe_float(item.get("current_price")), market_cap=safe_float(item.get("market_cap")), market_cap_rank=safe_int(item.get("market_cap_rank")), total_volume=safe_float(item.get("total_volume")), high_24h=safe_float(item.get("high_24h")), low_24h=safe_float(item.get("low_24h")), price_change_24h_pct=safe_float(item.get("price_change_percentage_24h")), price_change_7d_pct=safe_float(item.get("price_change_percentage_7d_in_currency")), sparkline=[safe_float(v) for v in spark])
