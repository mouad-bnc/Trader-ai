from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests


@dataclass(slots=True)
class BinanceBalance:
    asset: str
    free: float
    locked: float


class BinanceService:
    def __init__(self, api_key: str | None = None, api_secret: str | None = None, base_url: str = "https://api.binance.com", timeout: int = 8) -> None:
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def account_snapshot(self) -> list[BinanceBalance]:
        if not self.configured:
            return []
        payload = self._signed_get("/api/v3/account")
        balances = payload.get("balances", []) if isinstance(payload, dict) else []
        result: list[BinanceBalance] = []
        for row in balances:
            try:
                free = float(row.get("free", 0) or 0)
                locked = float(row.get("locked", 0) or 0)
                if free or locked:
                    result.append(BinanceBalance(str(row.get("asset", "")), free, locked))
            except (TypeError, ValueError):
                continue
        return result

    def trade_history(self, symbol: str | None = None) -> list[dict[str, Any]]:
        if not self.configured or not symbol:
            return []
        payload = self._signed_get("/api/v3/myTrades", {"symbol": symbol.upper(), "limit": 50})
        return payload if isinstance(payload, list) else []

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
