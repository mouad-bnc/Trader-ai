#!/usr/bin/env python3
"""
Crypto Trader Assistant v1
- Public Binance Spot data only
- No API key
- No order execution
- Educational assistant, not financial advice
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

import requests

BASE_URL = "https://api.binance.com"
DEFAULT_SYMBOLS = ["BTCUSDT", "SOLUSDT", "SUIUSDT", "DOGEUSDT"]


@dataclass
class Signal:
    symbol: str
    price: float
    change_24h_pct: float
    rsi_14: float
    sma_20: float
    distance_to_sma_pct: float
    volatility_20d_pct: float
    opportunity_score: int
    decision: str
    suggested_buy_zone: Tuple[float, float]
    risk_stop: float
    note: str


def get_json(path: str, params: Dict[str, str | int]) -> object:
    url = f"{BASE_URL}{path}"
    try:
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Erreur API Binance pour {url}: {exc}") from exc


def fetch_24h(symbol: str) -> Dict[str, str]:
    data = get_json("/api/v3/ticker/24hr", {"symbol": symbol})
    if not isinstance(data, dict):
        raise RuntimeError(f"Réponse inattendue pour ticker {symbol}")
    return data


def fetch_daily_closes(symbol: str, limit: int = 60) -> List[float]:
    data = get_json("/api/v3/klines", {"symbol": symbol, "interval": "1d", "limit": limit})
    if not isinstance(data, list) or len(data) < 21:
        raise RuntimeError(f"Pas assez de données kline pour {symbol}")
    return [float(candle[4]) for candle in data]


def sma(values: List[float], period: int) -> float:
    return sum(values[-period:]) / period


def rsi(values: List[float], period: int = 14) -> float:
    if len(values) <= period:
        return 50.0
    gains = []
    losses = []
    for previous, current in zip(values[-period - 1:-1], values[-period:]):
        diff = current - previous
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def volatility(values: List[float], period: int = 20) -> float:
    returns = []
    recent = values[-period - 1:]
    for previous, current in zip(recent[:-1], recent[1:]):
        if previous > 0:
            returns.append((current - previous) / previous)
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((x - mean) ** 2 for x in returns) / (len(returns) - 1)
    return math.sqrt(variance) * 100


def score_signal(price: float, change_24h_pct: float, rsi_14: float, sma_20_value: float, vol_20d_pct: float) -> Tuple[int, str, str]:
    score = 0
    notes = []

    distance_to_sma = ((price - sma_20_value) / sma_20_value) * 100

    if 35 <= rsi_14 <= 55:
        score += 2
        notes.append("RSI sain")
    elif 25 <= rsi_14 < 35:
        score += 3
        notes.append("potentiel rebond, mais prudent")
    elif rsi_14 > 70:
        score -= 2
        notes.append("risque de surchauffe")
    elif rsi_14 < 25:
        score -= 1
        notes.append("chute forte, attendre confirmation")

    if -6 <= distance_to_sma <= 2:
        score += 2
        notes.append("prix proche zone moyenne")
    elif distance_to_sma < -6:
        score += 1
        notes.append("prix sous moyenne, possible opportunité")
    elif distance_to_sma > 8:
        score -= 2
        notes.append("prix déjà éloigné de la moyenne")

    if -4 <= change_24h_pct <= 3:
        score += 1
        notes.append("variation 24h raisonnable")
    elif change_24h_pct > 8:
        score -= 2
        notes.append("hausse 24h trop rapide")
    elif change_24h_pct < -10:
        score -= 1
        notes.append("baisse 24h violente")

    if vol_20d_pct > 8:
        score -= 1
        notes.append("volatilité élevée")

    score = max(0, min(10, score + 3))

    if score >= 8:
        decision = "RENFORCER LÉGER"
    elif score >= 6:
        decision = "SURVEILLER / PETIT ACHAT POSSIBLE"
    elif score >= 4:
        decision = "ATTENDRE"
    else:
        decision = "NE RIEN FAIRE"

    return score, decision, ", ".join(notes)


def analyze_symbol(symbol: str) -> Signal:
    ticker = fetch_24h(symbol)
    closes = fetch_daily_closes(symbol)

    price = float(ticker["lastPrice"])
    change_24h_pct = float(ticker["priceChangePercent"])
    sma_20_value = sma(closes, 20)
    rsi_14_value = rsi(closes, 14)
    vol_20d_pct = volatility(closes, 20)
    distance_to_sma_pct = ((price - sma_20_value) / sma_20_value) * 100

    score, decision, note = score_signal(price, change_24h_pct, rsi_14_value, sma_20_value, vol_20d_pct)

    buy_low = sma_20_value * 0.94
    buy_high = sma_20_value * 1.01
    risk_stop = price * 0.92

    return Signal(
        symbol=symbol,
        price=price,
        change_24h_pct=change_24h_pct,
        rsi_14=rsi_14_value,
        sma_20=sma_20_value,
        distance_to_sma_pct=distance_to_sma_pct,
        volatility_20d_pct=vol_20d_pct,
        opportunity_score=score,
        decision=decision,
        suggested_buy_zone=(buy_low, buy_high),
        risk_stop=risk_stop,
        note=note,
    )


def fmt_price(value: float) -> str:
    if value >= 100:
        return f"{value:,.2f}"
    if value >= 1:
        return f"{value:,.4f}"
    return f"{value:,.6f}"


def print_report(signals: List[Signal], budget: float) -> None:
    print("\n=== Crypto Trader Assistant v1 ===")
    print("Mode: analyse uniquement. Aucun ordre n'est envoyé.\n")
    ranked = sorted(signals, key=lambda s: s.opportunity_score, reverse=True)

    for s in ranked:
        print(f"{s.symbol}")
        print(f"  Prix: {fmt_price(s.price)} USDT | 24h: {s.change_24h_pct:+.2f}%")
        print(f"  RSI 14j: {s.rsi_14:.1f} | SMA 20j: {fmt_price(s.sma_20)} | Distance SMA: {s.distance_to_sma_pct:+.2f}%")
        print(f"  Volatilité 20j: {s.volatility_20d_pct:.2f}%")
        print(f"  Score: {s.opportunity_score}/10 | Décision: {s.decision}")
        print(f"  Zone d'achat indicative: {fmt_price(s.suggested_buy_zone[0])} - {fmt_price(s.suggested_buy_zone[1])} USDT")
        print(f"  Stop risque indicatif: {fmt_price(s.risk_stop)} USDT")
        print(f"  Note: {s.note}\n")

    best = ranked[0]
    print("=== Suggestion budget ===")
    if best.opportunity_score >= 8:
        print(f"Meilleure opportunité: {best.symbol}. Allocation prudente suggérée: {budget * 0.40:.2f} USDT max.")
        print("Garde le reste en USDT pour une meilleure entrée ou une baisse du marché.")
    elif best.opportunity_score >= 6:
        print(f"Meilleure opportunité: {best.symbol}, mais signal moyen. Allocation prudente: {budget * 0.20:.2f} USDT max.")
    else:
        print("Aucune opportunité forte. Garder les USDT et attendre une meilleure zone.")

    print("\nImportant: ceci n'est pas un conseil financier. Utilise toujours une gestion du risque.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Crypto Trader Assistant v1")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS, help="Ex: BTCUSDT SOLUSDT SUIUSDT DOGEUSDT")
    parser.add_argument("--budget", type=float, default=100.0, help="Budget USDT à analyser")
    args = parser.parse_args()

    signals = []
    for symbol in args.symbols:
        try:
            signals.append(analyze_symbol(symbol.upper()))
        except Exception as exc:
            print(f"Erreur sur {symbol}: {exc}", file=sys.stderr)

    if not signals:
        print("Aucune donnée récupérée.", file=sys.stderr)
        return 1

    print_report(signals, args.budget)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
