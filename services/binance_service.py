from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import requests

from utils.helpers import safe_float


@dataclass(slots=True)
class BinanceBalance:
    asset: str
    free: float
    locked: float
    wallet: str = "Spot"

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
    wallet_amounts: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class BinancePortfolioSummary:
    positions: list[BinancePortfolioPosition]
    total_value_usdt: float
    pnl_24h_usdt: float | None = None
    pnl_24h_pct: float | None = None
    connected: bool = False
    status_message: str = "Connexion Binance indisponible"
    debug: dict[str, Any] = field(default_factory=dict)
    wallet_values_usdt: dict[str, float] = field(default_factory=dict)
    wallet_asset_counts: dict[str, int] = field(default_factory=dict)
    endpoint_warnings: list[str] = field(default_factory=list)
    last_sync_at: datetime | None = None

    @property
    def asset_count(self) -> int:
        return len(self.positions)

    @property
    def spot_value_usdt(self) -> float:
        return self.wallet_values_usdt.get("Spot", 0.0)

    @property
    def futures_value_usdt(self) -> float:
        return self.wallet_values_usdt.get("Futures", 0.0)

    @property
    def earn_value_usdt(self) -> float:
        return sum(self.wallet_values_usdt.get(name, 0.0) for name in ("Simple Earn", "Flexible Earn", "Locked Earn"))

    @property
    def funding_value_usdt(self) -> float:
        return self.wallet_values_usdt.get("Funding", 0.0)


class BinanceService:
    """Read-only Binance account synchronization across wallet families."""

    STABLE_USDT_PRICES = {"USDT": 1.0, "USDC": 1.0, "BUSD": 1.0, "FDUSD": 1.0, "TUSD": 1.0, "DAI": 1.0}

    READ_ONLY_ENDPOINTS: dict[str, tuple[str, str]] = {
        "Spot": ("GET", "/api/v3/account"),
        "Funding": ("POST", "/sapi/v1/asset/get-funding-asset"),
        "Simple Earn": ("GET", "/sapi/v1/simple-earn/account"),
        "Flexible Earn": ("GET", "/sapi/v1/simple-earn/flexible/position"),
        "Locked Earn": ("GET", "/sapi/v1/simple-earn/locked/position"),
        "Futures": ("GET", "/fapi/v3/balance"),
        "Margin": ("GET", "/sapi/v1/margin/account"),
        "Trading Bots": ("GET", "/sapi/v1/algo/spot/openOrders"),
    }

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
        summary = self.account_portfolio()
        return [BinanceBalance(position.asset, position.free, position.locked) for position in summary.positions]

    def spot_portfolio(self, coingecko: Any | None = None) -> BinancePortfolioSummary:
        """Backward-compatible alias for full account synchronization."""
        return self.account_portfolio(coingecko)

    def account_portfolio(self, coingecko: Any | None = None) -> BinancePortfolioSummary:
        if not self.configured:
            debug = self._debug_template()
            self.last_debug = debug
            return BinancePortfolioSummary([], 0.0, debug=debug)

        debug = self._debug_template()
        warnings: list[str] = []
        balances: list[BinanceBalance] = []
        endpoint_status: dict[str, Any] = {}

        for wallet, (method, path) in self.READ_ONLY_ENDPOINTS.items():
            payload, call_debug = self._signed_request(method, path, self._endpoint_params(wallet))
            endpoint_status[wallet] = {"status_code": call_debug.get("status_code"), "error": call_debug.get("error")}
            if call_debug.get("status_code") != 200:
                message = str(call_debug.get("error") or self._safe_error_message(payload, call_debug.get("status_code")))
                warnings.append(f"{wallet}: {message}")
                continue
            balances.extend(self._parse_wallet_balances(wallet, payload))

        debug["endpoints"] = endpoint_status
        debug["balances_returned"] = len(balances)
        debug["detected_symbols"] = self._first_detected_symbols([{"asset": b.asset} for b in balances])
        debug["non_zero_balances"] = len([b for b in balances if b.total > 0])
        debug["warnings"] = warnings

        positions = self._valued_positions(balances, coingecko)
        wallet_values = self._wallet_values(balances, positions)
        wallet_counts = self._wallet_counts(balances)
        total_value = sum(position.estimated_value_usdt for position in positions)
        total_pnl = sum(position.pnl_24h_usdt or 0.0 for position in positions if position.pnl_24h_usdt is not None)
        has_pnl = any(position.pnl_24h_usdt is not None for position in positions)
        pnl_pct = (total_pnl / (total_value - total_pnl) * 100) if has_pnl and (total_value - total_pnl) else None
        successful = any(item.get("status_code") == 200 for item in endpoint_status.values())
        connected = successful or bool(positions)
        status = f"{len(positions)} actifs synchronisés depuis Binance · Valeur totale estimée: {total_value:,.2f} USDT"
        if warnings:
            status += f" · {len(warnings)} avertissement(s) endpoint"
        if not positions and warnings:
            status = "Synchronisation partielle: aucun solde valorisable, mais certains endpoints Binance ont échoué."
        self.last_debug = debug
        return BinancePortfolioSummary(positions, total_value, total_pnl if has_pnl else None, pnl_pct, connected, status, debug, wallet_values, wallet_counts, warnings, datetime.now(timezone.utc))

    def _valued_positions(self, balances: list[BinanceBalance], coingecko: Any | None) -> list[BinancePortfolioPosition]:
        non_zero = [balance for balance in balances if balance.total > 0 and balance.asset]
        coingecko_prices = self._coingecko_prices(non_zero, coingecko) if non_zero else {}
        tickers = self._ticker_24h_by_symbol() if non_zero else {}
        grouped: dict[str, dict[str, Any]] = {}
        for balance in non_zero:
            row = grouped.setdefault(balance.asset, {"free": 0.0, "locked": 0.0, "wallets": {}})
            row["free"] += balance.free
            row["locked"] += balance.locked
            row["wallets"][balance.wallet] = row["wallets"].get(balance.wallet, 0.0) + balance.total
        positions: list[BinancePortfolioPosition] = []
        total_value = 0.0
        for asset, row in grouped.items():
            total = row["free"] + row["locked"]
            price = self._price_usdt(asset, coingecko_prices)
            value = total * price if price else 0.0
            pnl_pct = self._pnl_pct_24h(asset, tickers)
            pnl_value = None
            if value and pnl_pct is not None:
                previous_value = value / (1 + (pnl_pct / 100)) if pnl_pct > -100 else 0.0
                pnl_value = value - previous_value
            total_value += value
            positions.append(BinancePortfolioPosition(asset, row["free"], row["locked"], total, price, value, pnl_24h_usdt=pnl_value, pnl_24h_pct=pnl_pct, wallet_amounts=row["wallets"]))
        positions.sort(key=lambda p: p.estimated_value_usdt, reverse=True)
        for position in positions:
            position.allocation_pct = (position.estimated_value_usdt / total_value * 100) if total_value else 0.0
        return positions

    def _wallet_values(self, balances: list[BinanceBalance], positions: list[BinancePortfolioPosition]) -> dict[str, float]:
        prices = {position.asset: position.price_usdt for position in positions}
        values: dict[str, float] = {wallet: 0.0 for wallet in self.READ_ONLY_ENDPOINTS}
        for balance in balances:
            values[balance.wallet] = values.get(balance.wallet, 0.0) + balance.total * prices.get(balance.asset, 0.0)
        return values

    def _wallet_counts(self, balances: list[BinanceBalance]) -> dict[str, int]:
        assets_by_wallet: dict[str, set[str]] = {wallet: set() for wallet in self.READ_ONLY_ENDPOINTS}
        for balance in balances:
            if balance.total > 0:
                assets_by_wallet.setdefault(balance.wallet, set()).add(balance.asset)
        return {wallet: len(assets) for wallet, assets in assets_by_wallet.items()}

    def _endpoint_params(self, wallet: str) -> dict[str, Any]:
        if wallet in {"Flexible Earn", "Locked Earn"}:
            return {"size": 100}
        if wallet == "Funding":
            return {"needBtcValuation": "false"}
        return {}

    def _parse_wallet_balances(self, wallet: str, payload: Any) -> list[BinanceBalance]:
        if wallet == "Spot":
            return self._balances_from_rows(payload.get("balances", []) if isinstance(payload, dict) else [], wallet, "asset", "free", "locked")
        if wallet == "Funding":
            return self._balances_from_rows(payload if isinstance(payload, list) else [], wallet, "asset", "free", "locked")
        if wallet == "Simple Earn":
            rows = payload.get("totalAmountInUSDT", 0) if isinstance(payload, dict) else 0
            return [BinanceBalance("USDT", safe_float(rows), 0.0, wallet)] if safe_float(rows) > 0 else []
        if wallet in {"Flexible Earn", "Locked Earn"}:
            rows = payload.get("rows", []) if isinstance(payload, dict) else []
            return self._balances_from_rows(rows, wallet, "asset", "totalAmount")
        if wallet == "Futures":
            return self._balances_from_rows(payload if isinstance(payload, list) else [], wallet, "asset", "balance")
        if wallet == "Margin":
            rows = payload.get("userAssets", []) if isinstance(payload, dict) else []
            return self._balances_from_rows(rows, wallet, "asset", "free", "locked", extra_keys=("borrowed", "interest"), subtract_extra=True)
        return []

    def _balances_from_rows(self, rows: list[Any], wallet: str, asset_key: str, free_key: str, locked_key: str | None = None, extra_keys: tuple[str, ...] = (), subtract_extra: bool = False) -> list[BinanceBalance]:
        balances: list[BinanceBalance] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            asset = str(row.get(asset_key, "")).upper().strip()
            free = safe_float(row.get(free_key))
            locked = safe_float(row.get(locked_key)) if locked_key else 0.0
            extra = sum(safe_float(row.get(key)) for key in extra_keys)
            if subtract_extra:
                free = max(free - extra, 0.0)
            if asset and free + locked > 0:
                balances.append(BinanceBalance(asset, free, locked, wallet))
        return balances

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
        return self._signed_request("GET", path, params)

    def _signed_request(self, method: str, path: str, params: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
        debug = self._debug_template()
        if not self.configured:
            return {}, debug
        query = {**(params or {}), "recvWindow": 5000, "timestamp": self._timestamp_ms()}
        query["signature"] = self._signature(query)
        try:
            response = self._send_signed_http(method, path, query)
            debug["status_code"] = response.status_code
            payload = response.json() if response.content else {}
            if response.status_code == 400 and isinstance(payload, dict) and payload.get("code") == -1021:
                self._sync_server_time_offset()
                query = {**(params or {}), "recvWindow": 5000, "timestamp": self._timestamp_ms()}
                query["signature"] = self._signature(query)
                response = self._send_signed_http(method, path, query)
                debug["status_code"] = response.status_code
                payload = response.json() if response.content else {}
            return payload, debug
        except requests.RequestException:
            debug["error"] = "Connexion à Binance impossible."
            return {}, debug
        except ValueError:
            debug["error"] = "Réponse Binance illisible."
            return {}, debug

    def _send_signed_http(self, method: str, path: str, query: dict[str, Any]) -> requests.Response:
        headers = {"X-MBX-APIKEY": self.api_key}
        if method.upper() == "POST":
            return requests.post(f"{self.base_url}{path}", data=query, headers=headers, timeout=self.timeout)
        return requests.get(f"{self.base_url}{path}", params=query, headers=headers, timeout=self.timeout)

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
        return f"Erreur Binance {status_code or 'inconnue'}: endpoint indisponible."
