# Trader AI

**Version:** 1.0

Trader AI is a professional, mobile-first Streamlit crypto portfolio platform for educational research. It uses public CoinGecko market data, keeps portfolio editing local to the Streamlit session, and never places trades or requests exchange API keys.

## Features

- Modern dark responsive interface for desktop and mobile.
- Real editable portfolio table with quantity, average cost, notes, favorites, and alert thresholds.
- Binance Spot CSV import for balance snapshots (`Coin`, `Free`, `Locked`) and trade exports (`Base Asset`, `Side`, `Quantity`, `Price`).
- CoinGecko market data, trending assets, sparklines, market ranks, volume, and 24h/7d/30d performance.
- Portfolio value, cost basis, unrealized P&L, allocation, and estimated 7-day performance charts.
- Watchlists and favorite assets.
- Local price-alert highlighting when watched thresholds are crossed.
- Transparent AI-style opportunity scoring based on momentum, liquidity, volatility, rank, and drawdown.
- CSV export for backing up the local portfolio.
- Educational-only disclaimers throughout the app.

## Project structure

```text
.
├── app.py              # Streamlit UI and session workflow
├── analytics.py        # Portfolio analytics, alerts, and AI scoring rubric
├── coingecko.py        # Public CoinGecko client
├── portfolio_io.py     # Editable portfolio schema and Binance CSV import
├── sample_data.py      # Legacy compatibility wrapper returning an empty portfolio
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

```bash
streamlit run app.py
```

Open the local URL shown by Streamlit, typically `http://localhost:8501`.

## Streamlit Cloud deployment

1. Push this repository to GitHub.
2. In Streamlit Cloud, create an app from the repository.
3. Set the main file path to `app.py`.
4. Use the default Python dependency install from `requirements.txt`.

No secrets are required because the app does not use exchange APIs or private keys.

## Usage notes

1. Add CoinGecko IDs in the sidebar, such as `bitcoin`, `ethereum`, or `solana`.
2. Edit the portfolio table manually or import a Binance Spot CSV.
3. Add optional alert thresholds and mark favorites.
4. Review holdings, estimated performance, allocation, watchlists, market data, and AI opportunity scoring.
5. Export your portfolio CSV if you want to save your local session data.

## Data source and limitations

Trader AI uses only public CoinGecko endpoints. Public endpoints can be rate limited or temporarily unavailable. Binance CSV import is offline parsing of user-uploaded files; the app does not connect to Binance.

**Educational-only disclaimer:** Trader AI does not provide financial, investment, legal, or tax advice. AI opportunity scores are deterministic educational research rubrics and are not buy, sell, or hold recommendations.
