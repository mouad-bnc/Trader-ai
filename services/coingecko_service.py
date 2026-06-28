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
    is_fallback: bool = False


@dataclass(slots=True)
class FearGreed:
    value: int | None = None
    label: str = "Indisponible"


class CoinGeckoService:
    """CoinGecko market-data client with app-safe fallbacks.

    The primary path uses the public CoinGecko markets endpoint. If CoinGecko
    is temporarily unavailable or rate-limited, the service falls back to public
    Binance tickers for the same watchlist so pages can still render useful
    prices without exposing raw provider errors.
    """

    BINANCE_SYMBOLS = {
        "bitcoin": ("BTC", "Bitcoin", "BTCUSDT"),
        "ethereum": ("ETH", "Ethereum", "ETHUSDT"),
        "solana": ("SOL", "Solana", "SOLUSDT"),
        "sui": ("SUI", "Sui", "SUIUSDT"),
        "dogecoin": ("DOGE", "Dogecoin", "DOGEUSDT"),
        "ripple": ("XRP", "XRP", "XRPUSDT"),
    }

    def __init__(self, base_url: str = "https://api.coingecko.com/api/v3", timeout: int = 8) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            response = requests.get(f"{self.base_url}{path}", params=params or {}, timeout=self.timeout, headers={"accept": "application/json", "user-agent": "Trader-AI/3.0"})
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def get_markets(self, ids: list[str] | None = None, currency: str = DEFAULT_CURRENCY) -> list[MarketAsset]:
        requested_ids = ids or DEFAULT_SYMBOLS
        payload = self._get(
            "/coins/markets",
            {
                "vs_currency": currency,
                "ids": ",".join(requested_ids),
                "order": "market_cap_desc",
                "sparkline": "true",
                "price_change_percentage": "24h,7d",
                "per_page": len(requested_ids),
                "page": 1,
                "locale": "fr",
            },
        )
        if isinstance(payload, list) and payload:
            assets = [self._asset(item) for item in payload if isinstance(item, dict)]
            return self._order_watchlist(assets, requested_ids)
        return self._binance_market_fallback(requested_ids) or self._static_market_fallback(requested_ids)

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
        return MarketAsset(id=str(item.get("id", "")), symbol=str(item.get("symbol", "")).upper(), name=str(item.get("name", "Actif")), image=str(item.get("image", "")), current_price=safe_float(item.get("current_price")), market_cap=safe_float(item.get("market_cap")), market_cap_rank=safe_int(item.get("market_cap_rank")), total_volume=safe_float(item.get("total_volume")), high_24h=safe_float(item.get("high_24h")), low_24h=safe_float(item.get("low_24h")), price_change_24h_pct=safe_float(item.get("price_change_percentage_24h_in_currency", item.get("price_change_percentage_24h"))), price_change_7d_pct=safe_float(item.get("price_change_percentage_7d_in_currency")), sparkline=[safe_float(v) for v in spark])

    def _binance_market_fallback(self, ids: list[str]) -> list[MarketAsset]:
        try:
            response = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=self.timeout)
            response.raise_for_status()
            tickers = {str(item.get("symbol", "")).upper(): item for item in response.json() if isinstance(item, dict)}
        except Exception:
            return []
        assets: list[MarketAsset] = []
        for rank, coin_id in enumerate(ids, start=1):
            meta = self.BINANCE_SYMBOLS.get(coin_id)
            if not meta:
                continue
            symbol, name, pair = meta
            ticker = tickers.get(pair)
            if not ticker:
                continue
            last = safe_float(ticker.get("lastPrice"))
            assets.append(MarketAsset(id=coin_id, symbol=symbol, name=name, current_price=last, market_cap_rank=rank, total_volume=safe_float(ticker.get("quoteVolume")), high_24h=safe_float(ticker.get("highPrice")), low_24h=safe_float(ticker.get("lowPrice")), price_change_24h_pct=safe_float(ticker.get("priceChangePercent")), price_change_7d_pct=0.0, sparkline=[safe_float(ticker.get("openPrice")), last], is_fallback=True))
        return assets

    def _static_market_fallback(self, ids: list[str]) -> list[MarketAsset]:
        snapshots = {
            "bitcoin": ("BTC", "Bitcoin", 100000.0, 1, 0.0, 0.0, 1_000_000_000_000.0, 35_000_000_000.0),
            "ethereum": ("ETH", "Ethereum", 3500.0, 2, 0.0, 0.0, 420_000_000_000.0, 18_000_000_000.0),
            "solana": ("SOL", "Solana", 150.0, 5, 0.0, 0.0, 70_000_000_000.0, 4_000_000_000.0),
            "sui": ("SUI", "Sui", 3.0, 15, 0.0, 0.0, 9_000_000_000.0, 600_000_000.0),
            "dogecoin": ("DOGE", "Dogecoin", 0.18, 8, 0.0, 0.0, 25_000_000_000.0, 1_500_000_000.0),
            "ripple": ("XRP", "XRP", 0.60, 7, 0.0, 0.0, 35_000_000_000.0, 1_700_000_000.0),
        }
        assets: list[MarketAsset] = []
        for coin_id in ids:
            item = snapshots.get(coin_id)
            if not item:
                continue
            symbol, name, price, rank, change_24h, change_7d, market_cap, volume = item
            assets.append(MarketAsset(id=coin_id, symbol=symbol, name=name, current_price=price, market_cap_rank=rank, total_volume=volume, high_24h=price, low_24h=price, price_change_24h_pct=change_24h, price_change_7d_pct=change_7d, market_cap=market_cap, sparkline=[price, price], is_fallback=True))
        return assets

    def _order_watchlist(self, assets: list[MarketAsset], ids: list[str]) -> list[MarketAsset]:
        by_id = {asset.id: asset for asset in assets}
        return [by_id[coin_id] for coin_id in ids if coin_id in by_id]
