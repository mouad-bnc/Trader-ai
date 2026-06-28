from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
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
    debug: dict[str, Any] = field(default_factory=dict)


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
        self._server_time_offset_ms: int | None = None
        self.last_debug: dict[str, Any] = self._debug_template()

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def secrets_status(self) -> dict[str, bool]:
        return {"api_key_present": bool(self.api_key), "api_secret_present": bool(self.api_secret)}

    def account_snapshot(self) -> list[BinanceBalance]:
        """Return non-zero Spot balances from Binance account information."""
        summary = self.spot_portfolio()
        return [BinanceBalance(position.asset, position.free, position.locked) for position in summary.positions]

    def spot_portfolio(self, coingecko: Any | None = None) -> BinancePortfolioSummary:
        """Return Spot balances enriched with CoinGecko USDT valuation when available."""
        if not self.configured:
            debug = self._debug_template()
            self.last_debug = debug
            return BinancePortfolioSummary([], 0.0, debug=debug)

        payload, debug = self._signed_get("/api/v3/account")
        balances_payload = payload.get("balances", []) if isinstance(payload, dict) else []
        if not isinstance(balances_payload, list):
            debug["error"] = "Réponse Binance inattendue: balances indisponibles."
            self.last_debug = debug
            return BinancePortfolioSummary([], 0.0, connected=False, status_message=debug["error"], debug=debug)

        debug["balances_returned"] = len(balances_payload)
        debug["detected_symbols"] = self._first_detected_symbols(balances_payload)
        balances = self._non_zero_balances(balances_payload)
        debug["non_zero_balances"] = len(balances)

        if debug.get("status_code") != 200:
            status = str(debug.get("error") or "") or self._safe_error_message(payload, debug.get("status_code"))
            debug["error"] = status
            self.last_debug = debug
            return BinancePortfolioSummary([], 0.0, connected=False, status_message=status, debug=debug)

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
        status = f"{len(positions)} actifs Spot récupérés depuis Binance · Valeur estimée: {total_value:,.2f} USDT"
        self.last_debug = debug
        return BinancePortfolioSummary(positions, total_value, total_pnl_24h if has_pnl else None, pnl_pct_total, True, status, debug)

    def _first_detected_symbols(self, balances_payload: list[Any]) -> list[str]:
        symbols: list[str] = []
        for row in balances_payload:
            try:
                asset = str(row.get("asset", "")).upper().strip()
            except AttributeError:
                continue
            if asset:
                symbols.append(asset)
            if len(symbols) == 5:
                break
        return symbols

    def _non_zero_balances(self, balances_payload: list[Any]) -> list[BinanceBalance]:
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
        return balances

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

    def _signed_get(self, path: str, params: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
        debug = self._debug_template()
        if not self.configured:
            return {}, debug
        query = {**(params or {}), "recvWindow": 5000, "timestamp": self._timestamp_ms()}
        query["signature"] = self._signature(query)
        try:
            response = requests.get(f"{self.base_url}{path}", params=query, headers={"X-MBX-APIKEY": self.api_key}, timeout=self.timeout)
            debug["status_code"] = response.status_code
            payload = response.json() if response.content else {}
            if response.status_code == 400 and isinstance(payload, dict) and payload.get("code") == -1021:
                self._sync_server_time_offset()
                query = {**(params or {}), "recvWindow": 5000, "timestamp": self._timestamp_ms()}
                query["signature"] = self._signature(query)
                response = requests.get(f"{self.base_url}{path}", params=query, headers={"X-MBX-APIKEY": self.api_key}, timeout=self.timeout)
                debug["status_code"] = response.status_code
                payload = response.json() if response.content else {}
            return payload, debug
        except requests.RequestException:
            debug["error"] = "Connexion à Binance impossible."
            return {}, debug
        except ValueError:
            debug["error"] = "Réponse Binance illisible."
            return {}, debug

    def _timestamp_ms(self) -> int:
        offset = self._server_time_offset_ms
        if offset is None:
            offset = self._sync_server_time_offset()
        return int(time.time() * 1000) + offset

    def _sync_server_time_offset(self) -> int:
        try:
            response = requests.get(f"{self.base_url}/api/v3/time", timeout=self.timeout)
            response.raise_for_status()
            server_time = int(response.json().get("serverTime", 0))
            self._server_time_offset_ms = server_time - int(time.time() * 1000) if server_time else 0
        except Exception:
            self._server_time_offset_ms = 0
        return self._server_time_offset_ms

    def _signature(self, query: dict[str, Any]) -> str:
        return hmac.new(self.api_secret.encode(), urlencode(query).encode(), hashlib.sha256).hexdigest()

    def _debug_template(self) -> dict[str, Any]:
        return {**self.secrets_status(), "status_code": None, "error": "", "balances_returned": 0, "non_zero_balances": 0, "detected_symbols": []}

    def _safe_error_message(self, payload: Any, status_code: Any) -> str:
        if isinstance(payload, dict):
            code = payload.get("code")
            message = str(payload.get("msg") or "").strip()
            if code or message:
                return f"Erreur Binance {status_code or ''} ({code or 'sans code'}): {message or 'requête refusée'}."
        return f"Erreur Binance {status_code or 'inconnue'}: synchronisation Spot impossible."
