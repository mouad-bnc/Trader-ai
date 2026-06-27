"""Lecture sécurisée et optionnelle du portefeuille Spot Binance pour Trader."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import requests

BASE_URL = "https://api.binance.com"


@dataclass(frozen=True)
class BinanceAsset:
    """Actif Spot lu depuis Binance avec des permissions lecture seule."""

    symbol: str
    quantity: float
    current_price: float
    value: float


class BinanceReadOnlyClient:
    """Client Binance côté serveur, sans trading, futures ni retrait."""

    def __init__(self, timeout: int = 12) -> None:
        self.api_key = os.getenv("BINANCE_API_KEY", "").strip()
        self.api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
        self.timeout = timeout
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def _signed_get(self, path: str, params: dict[str, object] | None = None) -> object:
        if not self.configured:
            raise RuntimeError("Connexion Binance non configurée.")
        payload = {"timestamp": int(time.time() * 1000), "recvWindow": 5000, **(params or {})}
        query = urlencode(payload)
        signature = hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        response = self.session.get(f"{BASE_URL}{path}?{query}&signature={signature}", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _public_prices(self) -> dict[str, float]:
        response = self.session.get(f"{BASE_URL}/api/v3/ticker/price", timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            return {}
        return {str(item.get("symbol")): float(item.get("price") or 0) for item in data if isinstance(item, dict)}

    def spot_assets(self) -> list[BinanceAsset]:
        """Retourne les soldes Spot non nuls valorisés en USDT, sans action d’ordre."""

        account = self._signed_get("/api/v3/account", {"omitZeroBalances": "true"})
        balances = account.get("balances", []) if isinstance(account, dict) else []
        prices = self._public_prices()
        assets: list[BinanceAsset] = []
        for row in balances:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("asset", "")).upper()
            quantity = float(row.get("free") or 0) + float(row.get("locked") or 0)
            if not symbol or quantity <= 0:
                continue
            price = 1.0 if symbol in {"USDT", "USDC", "FDUSD", "BUSD"} else prices.get(f"{symbol}USDT", 0.0)
            assets.append(BinanceAsset(symbol=symbol, quantity=quantity, current_price=price, value=quantity * price))
        return sorted(assets, key=lambda asset: asset.value, reverse=True)
