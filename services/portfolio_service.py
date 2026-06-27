"""Service central du portefeuille pour Trader."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
import requests

from binance import BinanceAsset, BinanceReadOnlyClient
from coingecko import MarketCoin
from portfolio_analytics import enrich_portfolio, triggered_alerts
from portfolio_io import SYMBOL_TO_COINGECKO_ID, empty_portfolio, normalize_portfolio, parse_binance_spot_csv


@dataclass(frozen=True)
class PortfolioData:
    """Structure unique consommée par les pages portefeuille et accueil."""

    holdings: pd.DataFrame
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    daily_pnl: float
    daily_pnl_pct: float
    alerts: pd.DataFrame
    favorite_ids: set[str]
    best_row: pd.DataFrame
    worst_row: pd.DataFrame
    allocation: dict[str, float]
    exposure: dict[str, float]


STABLECOIN_IDS = {"USDT": "tether", "USDC": "usd-coin", "FDUSD": "first-digital-usd", "BUSD": "binance-usd", "DAI": "dai"}


@dataclass(frozen=True)
class BinanceSyncResult:
    """Résultat propre de synchronisation Binance conservé en session."""

    portfolio: pd.DataFrame
    synced_at: str | None
    connection_status: str
    message: str


class PortfolioService:
    """Source de vérité pour chargement, import, Binance et métriques portefeuille."""

    def __init__(self, binance_client: BinanceReadOnlyClient | None = None) -> None:
        self.binance_client = binance_client or BinanceReadOnlyClient()

    @property
    def binance_configured(self) -> bool:
        return self.binance_client.configured

    def empty(self) -> pd.DataFrame:
        return empty_portfolio()

    def load(self, frame: pd.DataFrame) -> pd.DataFrame:
        return normalize_portfolio(frame)

    def import_csv(self, uploaded_file) -> pd.DataFrame:
        return parse_binance_spot_csv(uploaded_file)

    def binance_assets(self) -> list[BinanceAsset]:
        return self.binance_client.spot_assets()

    def sync_binance_portfolio(self) -> BinanceSyncResult:
        """Synchronise le portefeuille Spot Binance en lecture seule vers le format unique de l'app."""

        if not self.binance_configured:
            return BinanceSyncResult(
                portfolio=self.empty(),
                synced_at=None,
                connection_status="not_configured",
                message="Connexion Binance non configurée.",
            )

        try:
            assets = self.binance_assets()
        except requests.Timeout:
            return self._sync_error("timeout", "Binance ne répond pas pour le moment. Réessaie dans quelques instants.")
        except requests.ConnectionError:
            return self._sync_error("network_error", "Connexion réseau indisponible. Vérifie la connexion au serveur.")
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in {401, 403}:
                return self._sync_error("invalid_keys", "Clés Binance invalides ou permissions lecture seule insuffisantes.")
            if status_code in {418, 429, 500, 502, 503, 504}:
                return self._sync_error("api_unavailable", "API Binance momentanément indisponible. Réessaie plus tard.")
            return self._sync_error("binance_error", "Synchronisation Binance impossible pour le moment.")
        except requests.RequestException:
            return self._sync_error("network_error", "Connexion Binance indisponible. Réessaie dans quelques instants.")
        except Exception:
            return self._sync_error("binance_error", "Synchronisation Binance impossible. Vérifie la configuration Binance.")

        rows = []
        for asset in assets:
            if asset.quantity <= 0 or asset.value <= 0:
                continue
            coin_id = STABLECOIN_IDS.get(asset.symbol) or SYMBOL_TO_COINGECKO_ID.get(asset.symbol, asset.symbol.lower())
            rows.append(
                {
                    "coin_id": coin_id,
                    "symbol": asset.symbol,
                    "quantity": asset.quantity,
                    "avg_cost": asset.current_price,
                    "alert_below": 0.0,
                    "alert_above": 0.0,
                    "favorite": False,
                    "notes": "Synchronisé depuis Binance Spot",
                }
            )

        return BinanceSyncResult(
            portfolio=normalize_portfolio(pd.DataFrame(rows)),
            synced_at=datetime.now(timezone.utc).isoformat(),
            connection_status="connected",
            message="Portefeuille Binance synchronisé",
        )


    def sync_portfolio(self) -> BinanceSyncResult:
        """Alias de compatibilité pour les anciens appels de synchronisation Binance."""

        return self.sync_binance_portfolio()

    def _sync_error(self, status: str, message: str) -> BinanceSyncResult:
        return BinanceSyncResult(portfolio=self.empty(), synced_at=None, connection_status=status, message=message)

    def build_data(self, holdings: pd.DataFrame, markets: list[MarketCoin], market_lookup: dict[str, MarketCoin]) -> PortfolioData:
        normalized = normalize_portfolio(holdings)
        enriched = enrich_portfolio(normalized, markets)
        total_value = float(enriched["value"].sum()) if not enriched.empty else 0.0
        total_cost = float(enriched["cost_basis"].sum()) if not enriched.empty else 0.0
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0.0
        daily_pnl = sum(
            float(row["value"]) * (float(market_lookup[row["coin_id"]].price_change_24h_pct) / 100)
            for _, row in enriched.iterrows()
            if row["coin_id"] in market_lookup
        )
        daily_pnl_pct = (daily_pnl / max(total_value - daily_pnl, 1) * 100) if total_value else 0.0
        favorite_ids = set(normalized.loc[normalized["favorite"], "coin_id"]) if not normalized.empty else set()
        best_row = enriched.sort_values("pnl_pct", ascending=False).head(1) if not enriched.empty else pd.DataFrame()
        worst_row = enriched.sort_values("pnl_pct", ascending=True).head(1) if not enriched.empty else pd.DataFrame()
        allocation = self._allocation(enriched, total_value)
        exposure = self._exposure(enriched, total_value)
        return PortfolioData(enriched, total_value, total_cost, total_pnl, total_pnl_pct, daily_pnl, daily_pnl_pct, triggered_alerts(normalized, markets), favorite_ids, best_row, worst_row, allocation, exposure)

    def segment_allocation(self, total: float) -> dict[str, float]:
        if total <= 0:
            return {"Spot": 0, "Earn": 0, "Bots": 0}
        return {"Spot": total * .72, "Earn": total * .18, "Bots": total * .10}

    @staticmethod
    def _allocation(portfolio: pd.DataFrame, total: float) -> dict[str, float]:
        if portfolio.empty or total <= 0:
            return {}
        return {str(row["symbol"]): float(row["value"]) / total * 100 for _, row in portfolio.iterrows()}

    @staticmethod
    def _exposure(portfolio: pd.DataFrame, total: float) -> dict[str, float]:
        if portfolio.empty or total <= 0:
            return {"crypto": 0.0, "cash": 0.0}
        cash_symbols = {"USDT", "USDC", "FDUSD", "BUSD", "USD", "EUR"}
        cash = sum(float(row["value"]) for _, row in portfolio.iterrows() if str(row["symbol"]).upper() in cash_symbols)
        return {"crypto": max(total - cash, 0.0), "cash": cash}


def sync_binance_portfolio(binance_client: BinanceReadOnlyClient | None = None) -> BinanceSyncResult:
    """Synchronise Binance Spot via le service portefeuille central."""

    return PortfolioService(binance_client).sync_binance_portfolio()


def sync_portfolio(binance_client: BinanceReadOnlyClient | None = None) -> BinanceSyncResult:
    """Alias de compatibilité pour les anciens appels de synchronisation Binance."""

    return sync_binance_portfolio(binance_client)


__all__ = ["BinanceSyncResult", "PortfolioData", "PortfolioService", "sync_binance_portfolio", "sync_portfolio"]
