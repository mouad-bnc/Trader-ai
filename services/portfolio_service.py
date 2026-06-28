from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from services.coingecko_service import MarketAsset
from utils.helpers import safe_float


@dataclass(slots=True)
class Holding:
    symbol: str
    name: str
    quantity: float
    avg_cost: float


@dataclass(slots=True)
class Position:
    holding: Holding
    price: float
    value: float
    cost: float
    pnl: float
    pnl_pct: float
    allocation_pct: float = 0.0


@dataclass(slots=True)
class PortfolioSummary:
    positions: list[Position]
    total_value: float
    total_cost: float
    pnl: float
    pnl_pct: float


class PortfolioService:
    def demo_holdings(self) -> list[Holding]:
        return [Holding("BTC", "Bitcoin", 0.035, 62500), Holding("ETH", "Ethereum", 0.72, 3200), Holding("SOL", "Solana", 8.5, 145)]

    def summarize(self, holdings: Iterable[Holding] | None, markets: list[MarketAsset] | None = None) -> PortfolioSummary:
        market_by_symbol = {asset.symbol.upper(): asset for asset in markets or []}
        positions: list[Position] = []
        total_value = 0.0
        total_cost = 0.0
        for holding in holdings or []:
            asset = market_by_symbol.get(holding.symbol.upper())
            price = asset.current_price if asset and asset.current_price else holding.avg_cost
            value = safe_float(holding.quantity) * safe_float(price)
            cost = safe_float(holding.quantity) * safe_float(holding.avg_cost)
            pnl = value - cost
            pnl_pct = (pnl / cost * 100) if cost else 0.0
            positions.append(Position(holding, price, value, cost, pnl, pnl_pct))
            total_value += value
            total_cost += cost
        for position in positions:
            position.allocation_pct = (position.value / total_value * 100) if total_value else 0.0
        pnl = total_value - total_cost
        return PortfolioSummary(positions, total_value, total_cost, pnl, (pnl / total_cost * 100) if total_cost else 0.0)

    def allocation(self, summary: PortfolioSummary) -> dict[str, float]:
        return {position.holding.symbol: position.allocation_pct for position in summary.positions}
