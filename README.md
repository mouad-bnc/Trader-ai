# Trader AI

**Version:** 0.2

Trader AI is a mobile-first Streamlit crypto dashboard designed to feel like a real iPhone crypto app while staying educational only. It uses the public CoinGecko API, requires no API keys, never connects to Binance, and never places trades.

## Mobile-first features

- iPhone-optimized layout targeting narrow Safari widths such as 390px.
- Compact dark Binance-inspired cards with no wide market tables on mobile.
- Portfolio summary pinned at the top of the experience.
- Large touch-friendly refresh and input controls.
- Bottom mobile navigation for Portfolio, Markets, Signals, and Setup.
- Sticky refresh/action button for quick public market data reloads.
- Manual portfolio editor for local quantity and average-cost tracking.
- Holdings cards with current value, allocation, and unrealized P&L.
- P&L color rules: green for gains and red for losses.
- Markets rendered as mobile cards with price, rank, 24h, 7d, 30d, volume, and market cap.
- Educational opportunity signals built from public CoinGecko market fields.

## Guardrails

Trader AI intentionally keeps the app safe and simple:

- CoinGecko API only.
- No Binance API.
- No exchange API keys.
- No automated trading.
- No trade execution.
- Educational research only; not financial advice.

## Project structure

```text
.
├── app.py
├── analytics.py
├── coingecko.py
├── sample_data.py
├── requirements.txt
├── README.md
└── pyproject.toml
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

## 390px mobile layout check

To review the iPhone-width layout locally:

1. Start the app with `streamlit run app.py`.
2. Open browser developer tools.
3. Enable device emulation and set the viewport width to `390px`.
4. Confirm the bottom nav remains fixed, the refresh action is touch-friendly, market data appears as stacked cards, and the page does not horizontally scroll.

## Usage notes

1. Enter CoinGecko coin IDs in the sidebar, such as `bitcoin`, `ethereum`, or `solana`.
2. Optionally include CoinGecko trending coins.
3. Edit the manual portfolio table with quantity and average cost.
4. Review portfolio value, unrealized P&L, allocation, mobile market cards, and educational opportunity signals.

## Data source and limitations

Trader AI uses only public CoinGecko endpoints. Public endpoints can be rate limited or temporarily unavailable. The recommendation engine is educational and should not be treated as financial advice.

## Streamlit Cloud

The app is Streamlit Cloud compatible. Deploy the repository with `app.py` as the entry point and install dependencies from `requirements.txt`.
