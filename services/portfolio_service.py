"""Service central du portefeuille pour Trader."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from binance import BinanceAsset, BinanceReadOnlyClient
from coingecko import MarketCoin
from portfolio_analytics import enrich_portfolio, triggered_alerts
from portfolio_io import empty_portfolio, normalize_portfolio, parse_binance_spot_csv


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


__all__ = ["PortfolioData", "PortfolioService"]
