from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests

from utils.helpers import safe_float


@dataclass(slots=True)
class BinanceBalance:
    asset: str
    free: float
    locked: float

    @property
    def total(self) -> float:
        return self.free + self.locked


@dataclass(slots=True)
class BinancePortfolioPosition:
    asset: str
    free: float
    locked: float
    total: float
    price_usdt: float
    estimated_value_usdt: float
    allocation_pct: float = 0.0
    pnl_24h_usdt: float | None = None
    pnl_24h_pct: float | None = None


@dataclass(slots=True)
class BinancePortfolioSummary:
    positions: list[BinancePortfolioPosition]
    total_value_usdt: float
    pnl_24h_usdt: float | None = None
    pnl_24h_pct: float | None = None
    connected: bool = False
    status_message: str = "Connexion Binance indisponible"


class BinanceService:
    """Read-only Binance Spot account integration.

    This service only calls the signed Spot account information endpoint and
    public market-data endpoints. It does not implement trading, transfer, or
    withdrawal endpoints.
    """

    STABLE_USDT_PRICES = {"USDT": 1.0, "USDC": 1.0, "BUSD": 1.0, "FDUSD": 1.0, "TUSD": 1.0, "DAI": 1.0}

    def __init__(self, api_key: str | None = None, api_secret: str | None = None, base_url: str = "https://api.binance.com", timeout: int = 8) -> None:
        self.api_key = (api_key or "").strip()
        self.api_secret = (api_secret or "").strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def account_snapshot(self) -> list[BinanceBalance]:
        """Return non-zero Spot balances from Binance account information."""
        if not self.configured:
            return []
        payload = self._signed_get("/api/v3/account")
        balances = payload.get("balances", []) if isinstance(payload, dict) else []
        result: list[BinanceBalance] = []
        for row in balances:
            try:
                free = safe_float(row.get("free"))
                locked = safe_float(row.get("locked"))
                asset = str(row.get("asset", "")).upper().strip()
                if asset and free + locked > 0:
                    result.append(BinanceBalance(asset, free, locked))
            except (AttributeError, TypeError, ValueError):
                continue
        return result

    def spot_portfolio(self, coingecko: Any | None = None) -> BinancePortfolioSummary:
        """Return Spot balances enriched with CoinGecko USDT valuation when available."""
        if not self.configured:
            return BinancePortfolioSummary([], 0.0)
        payload = self._signed_get("/api/v3/account")
        balances_payload = payload.get("balances", []) if isinstance(payload, dict) else []
        if not isinstance(balances_payload, list):
            return BinancePortfolioSummary([], 0.0)

        balances: list[BinanceBalance] = []
        for row in balances_payload:
            try:
                free = safe_float(row.get("free"))
                locked = safe_float(row.get("locked"))
                asset = str(row.get("asset", "")).upper().strip()
                if asset and free + locked > 0:
                    balances.append(BinanceBalance(asset, free, locked))
            except (AttributeError, TypeError, ValueError):
                continue

        coingecko_prices = self._coingecko_prices(balances, coingecko) if balances else {}
        tickers = self._ticker_24h_by_symbol() if balances else {}
        positions: list[BinancePortfolioPosition] = []
        total_value = 0.0
        total_pnl_24h = 0.0
        has_pnl = False

        for balance in balances:
            price = self._price_usdt(balance.asset, coingecko_prices)
            value = balance.total * price if price else 0.0
            pnl_pct = self._pnl_pct_24h(balance.asset, tickers)
            pnl_value = None
            if value and pnl_pct is not None:
                previous_value = value / (1 + (pnl_pct / 100)) if pnl_pct > -100 else 0.0
                pnl_value = value - previous_value
                total_pnl_24h += pnl_value
                has_pnl = True
            total_value += value
            positions.append(BinancePortfolioPosition(balance.asset, balance.free, balance.locked, balance.total, price, value, pnl_24h_usdt=pnl_value, pnl_24h_pct=pnl_pct))

        positions.sort(key=lambda position: position.estimated_value_usdt, reverse=True)
        for position in positions:
            position.allocation_pct = (position.estimated_value_usdt / total_value * 100) if total_value else 0.0
        pnl_pct_total = (total_pnl_24h / (total_value - total_pnl_24h) * 100) if has_pnl and (total_value - total_pnl_24h) else None
        return BinancePortfolioSummary(positions, total_value, total_pnl_24h if has_pnl else None, pnl_pct_total, True, "Binance connecté en lecture seule")

    def _ticker_24h_by_symbol(self) -> dict[str, dict[str, Any]]:
        payload = self._public_get("/api/v3/ticker/24hr")
        if not isinstance(payload, list):
            return {}
        return {str(item.get("symbol", "")).upper(): item for item in payload if isinstance(item, dict)}

    def _coingecko_prices(self, balances: list[BinanceBalance], coingecko: Any | None) -> dict[str, float]:
        if coingecko is None or not hasattr(coingecko, "prices_by_symbols"):
            return {}
        symbols = [balance.asset for balance in balances if balance.asset not in self.STABLE_USDT_PRICES]
        try:
            return coingecko.prices_by_symbols(symbols)
        except Exception:
            return {}

    def _price_usdt(self, asset: str, coingecko_prices: dict[str, float]) -> float:
        asset = asset.upper()
        if asset in self.STABLE_USDT_PRICES:
            return self.STABLE_USDT_PRICES[asset]
        return safe_float(coingecko_prices.get(asset))

    def _pnl_pct_24h(self, asset: str, tickers: dict[str, dict[str, Any]]) -> float | None:
        asset = asset.upper()
        if asset in self.STABLE_USDT_PRICES:
            return 0.0
        ticker = tickers.get(f"{asset}USDT")
        if not ticker:
            return None
        return safe_float(ticker.get("priceChangePercent"))

    def _public_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            response = requests.get(f"{self.base_url}{path}", params=params or {}, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def _signed_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = {**(params or {}), "timestamp": int(time.time() * 1000)}
        signature = hmac.new(self.api_secret.encode(), urlencode(query).encode(), hashlib.sha256).hexdigest()
        query["signature"] = signature
        try:
            response = requests.get(f"{self.base_url}{path}", params=query, headers={"X-MBX-APIKEY": self.api_key}, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}
