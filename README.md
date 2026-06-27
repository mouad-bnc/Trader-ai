# Trader AI

**Version:** 0.1

Trader AI is a clean, production-ready Streamlit crypto dashboard built from scratch. It uses the public CoinGecko API only, requires no API keys, and never connects to Binance or any exchange account.

## Features

- Dark modern Streamlit UI with responsive layout for desktop and mobile.
- CoinGecko-only market dashboard.
- Manual editable portfolio.
- Live portfolio value.
- Unrealized P&L and P&L percentage.
- Allocation breakdown.
- Opportunity score for tracked coins.
- Recommendation engine with clear rationale.
- No Binance API, no API keys, and no automated trading.

## Project structure

```text
.
├── app.py
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml
└── src/
    └── trader_ai/
        ├── __init__.py
        ├── analytics.py
        ├── coingecko.py
        └── sample_data.py
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Run

```bash
streamlit run app.py
```

Open the local URL shown by Streamlit, typically `http://localhost:8501`.

## Usage notes

1. Enter CoinGecko coin IDs in the sidebar, such as `bitcoin`, `ethereum`, or `solana`.
2. Edit the manual portfolio table with your quantity and average cost.
3. Review total value, unrealized P&L, allocation, opportunity scores, and recommendations.

## Data source and limitations

Trader AI uses only public CoinGecko endpoints. Public endpoints can be rate limited or temporarily unavailable. The recommendation engine is educational and should not be treated as financial advice.
