"""Service central des données de marché pour Trader."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import requests
import streamlit as st

from coingecko import DEFAULT_COINS, CoinGeckoClient, MarketCoin, markets_to_frame


class MarketService:
    """Unique point d'accès aux prix, tendances et indicateurs de marché."""

    def __init__(self, client: CoinGeckoClient | None = None) -> None:
        self.client = client or CoinGeckoClient()

    def trending_ids(self, limit: int = 7) -> list[str]:
        return _cached_trending_ids(limit)

    def prices(self, coin_ids: Iterable[str], currency: str = "usd") -> pd.DataFrame:
        ids = tuple(dict.fromkeys(coin.strip().lower() for coin in coin_ids if coin.strip()))
        return _cached_market_prices(ids, currency.lower())

    def market_objects(self, market_frame: pd.DataFrame) -> list[MarketCoin]:
        return [MarketCoin(**row.to_dict()) for _, row in market_frame.iterrows()]

    def market_lookup(self, markets: list[MarketCoin]) -> dict[str, MarketCoin]:
        return {coin.coin_id: coin for coin in markets}

    def fear_greed(self) -> tuple[int | None, str]:
        return _cached_fear_greed()

    def btc_dominance(self, markets: list[MarketCoin]) -> float:
        total = sum(max(coin.market_cap, 0) for coin in markets)
        btc = next((coin.market_cap for coin in markets if coin.coin_id == "bitcoin"), 0)
        return (btc / total * 100) if total else 0

    def clear_cache(self) -> None:
        _cached_market_prices.clear()
        _cached_trending_ids.clear()
        _cached_fear_greed.clear()


@st.cache_data(ttl=90, show_spinner=False)
def _cached_market_prices(ids: tuple[str, ...], currency: str) -> pd.DataFrame:
    client = CoinGeckoClient()
    return markets_to_frame(client.fetch_markets(ids, currency=currency))


@st.cache_data(ttl=300, show_spinner=False)
def _cached_trending_ids(limit: int = 7) -> list[str]:
    client = CoinGeckoClient()
    return client.trending_ids(limit=limit)


@st.cache_data(ttl=900, show_spinner=False)
def _cached_fear_greed() -> tuple[int | None, str]:
    """Lit l'indice public Fear & Greed sans inventer de valeur."""
    try:
        response = requests.get("https://api.alternative.me/fng/", params={"limit": 1, "format": "json"}, timeout=8)
        response.raise_for_status()
        payload = response.json()
        latest = (payload.get("data") or [{}])[0]
        return int(latest.get("value")), str(latest.get("value_classification") or "Marché")
    except Exception:
        return None, "Indisponible"


__all__ = ["DEFAULT_COINS", "MarketCoin", "MarketService"]
