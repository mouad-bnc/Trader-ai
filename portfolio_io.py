"""Portfolio import/export helpers for Trader AI."""

from __future__ import annotations

from io import StringIO

import pandas as pd

PORTFOLIO_COLUMNS = ["coin_id", "symbol", "quantity", "avg_cost", "alert_below", "alert_above", "favorite", "notes"]
SYMBOL_TO_COINGECKO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "MATIC": "matic-network",
    "POL": "polygon-ecosystem-token",
    "LINK": "chainlink",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "SUI": "sui",
    "TRX": "tron",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "UNI": "uniswap",
    "AAVE": "aave",
    "RENDER": "render-token",
    "RNDR": "render-token",
    "NEAR": "near",
    "ATOM": "cosmos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "SEI": "sei-network",
}


def empty_portfolio() -> pd.DataFrame:
    """Return an empty editable portfolio with stable Streamlit columns."""

    return pd.DataFrame(columns=PORTFOLIO_COLUMNS).astype(
        {
            "coin_id": "string",
            "symbol": "string",
            "quantity": "float64",
            "avg_cost": "float64",
            "alert_below": "float64",
            "alert_above": "float64",
            "favorite": "bool",
            "notes": "string",
        }
    )


def normalize_portfolio(frame: pd.DataFrame) -> pd.DataFrame:
    """Coerce user-edited portfolio rows into a safe canonical schema."""

    normalized = empty_portfolio()
    if frame is None or frame.empty:
        return normalized
    for column in PORTFOLIO_COLUMNS:
        normalized[column] = frame[column] if column in frame.columns else normalized[column]
    normalized["coin_id"] = normalized["coin_id"].fillna("").astype(str).str.strip().str.lower()
    normalized["symbol"] = normalized["symbol"].fillna("").astype(str).str.strip().str.upper()
    for column in ["quantity", "avg_cost", "alert_below", "alert_above"]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce").fillna(0.0)
    normalized["favorite"] = normalized["favorite"].fillna(False).astype(bool)
    normalized["notes"] = normalized["notes"].fillna("").astype(str)
    normalized = normalized[(normalized["coin_id"] != "") & (normalized["quantity"] >= 0)]
    return normalized.reset_index(drop=True)


def parse_binance_spot_csv(uploaded_file) -> pd.DataFrame:
    """Parse common Binance Spot account/export CSV files into portfolio rows.

    Supported exports include Spot account snapshots with Coin/Free/Locked columns
    and trade exports with Base Asset, Quote Asset, Quantity, Price, and side fields.
    Trade imports estimate average cost from BUY rows and net out SELL quantities.
    """

    raw = uploaded_file.getvalue().decode("utf-8-sig")
    frame = pd.read_csv(StringIO(raw))
    lower_map = {str(col).strip().lower(): col for col in frame.columns}

    if {"coin", "free"}.issubset(lower_map):
        coin_col = lower_map["coin"]
        free_col = lower_map["free"]
        locked_col = lower_map.get("locked")
        rows = []
        for _, row in frame.iterrows():
            symbol = str(row.get(coin_col, "")).upper().strip()
            if not symbol or symbol in {"USDT", "USDC", "BUSD", "FDUSD", "TUSD", "DAI"}:
                continue
            quantity = float(pd.to_numeric(row.get(free_col, 0), errors="coerce") or 0)
            if locked_col:
                quantity += float(pd.to_numeric(row.get(locked_col, 0), errors="coerce") or 0)
            if quantity > 0:
                rows.append(_row_from_symbol(symbol, quantity, 0.0))
        return normalize_portfolio(pd.DataFrame(rows))

    base_col = next((lower_map[name] for name in ["base asset", "baseasset", "base"] if name in lower_map), None)
    side_col = next((lower_map[name] for name in ["side", "type"] if name in lower_map), None)
    qty_col = next((lower_map[name] for name in ["quantity", "executed", "amount"] if name in lower_map), None)
    price_col = next((lower_map[name] for name in ["price", "average price", "avg price"] if name in lower_map), None)
    if base_col and side_col and qty_col:
        positions: dict[str, dict[str, float]] = {}
        for _, row in frame.iterrows():
            symbol = str(row.get(base_col, "")).upper().strip()
            quantity = float(pd.to_numeric(row.get(qty_col, 0), errors="coerce") or 0)
            price = float(pd.to_numeric(row.get(price_col, 0), errors="coerce") or 0) if price_col else 0.0
            side = str(row.get(side_col, "")).upper()
            if not symbol or quantity <= 0:
                continue
            pos = positions.setdefault(symbol, {"quantity": 0.0, "cost": 0.0})
            if "SELL" in side:
                sell_qty = min(quantity, pos["quantity"])
                avg = pos["cost"] / pos["quantity"] if pos["quantity"] else 0.0
                pos["quantity"] -= sell_qty
                pos["cost"] -= sell_qty * avg
            else:
                pos["quantity"] += quantity
                pos["cost"] += quantity * price
        rows = [_row_from_symbol(sym, data["quantity"], data["cost"] / data["quantity"] if data["quantity"] else 0.0) for sym, data in positions.items() if data["quantity"] > 0]
        return normalize_portfolio(pd.DataFrame(rows))

    raise ValueError("Unsupported Binance CSV. Upload a Spot balance CSV with Coin/Free/Locked columns or a trade CSV with Base Asset/Side/Quantity/Price columns.")


def _row_from_symbol(symbol: str, quantity: float, avg_cost: float) -> dict[str, object]:
    return {
        "coin_id": SYMBOL_TO_COINGECKO_ID.get(symbol, symbol.lower()),
        "symbol": symbol,
        "quantity": quantity,
        "avg_cost": avg_cost,
        "alert_below": 0.0,
        "alert_above": 0.0,
        "favorite": False,
        "notes": "Imported from Binance CSV",
    }
