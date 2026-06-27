# Trader AI

**Version:** 3.0

Trader AI is a premium, mobile-first Streamlit crypto intelligence application for educational research. It uses public CoinGecko market data, keeps portfolio editing local to the Streamlit session, and never places trades, requests exchange API keys, or connects to a trading API.

## Product experience

- Premium dark design system with black backgrounds, glass cards, soft shadows, gold accents, green gains, and red losses.
- iPhone Safari-first layout targeting 390px screens, fixed icon-only bottom navigation, large touch targets, and no horizontal scrolling.
- Home dashboard with a personal greeting, portfolio value, daily P&L, total return, refresh affordance, and notification icon.
- Portfolio card with total value, daily gain, total gain, allocation leader, top performer, worst performer, and a mini performance chart.
- Markets screen with card-based assets instead of tables. Each card includes coin logo, name, ticker, price, 24h and 7d performance, mini chart, market rank, volume, AI score, opportunity badge, risk badge, and favorite state.
- Watchlist screen with search, add/remove favorites, sorting, filtering, and swipe-style premium cards.
- Dedicated AI Intelligence screen with opportunity, trend, momentum, risk-control, and confidence scores plus a simple natural-language explanation.
- Settings for theme, currency, refresh interval, about details, and the educational disclaimer.
- Smooth transitions, button animations, card hover states, progress bars, and loading skeleton styling.

## Data and safety principles

- CoinGecko remains the only live market data provider.
- No Binance API or trading API is used.
- No custody, order placement, or exchange account connection exists.
- CSV import is offline parsing only for educational portfolio setup.
- AI scores are deterministic educational rubrics, not financial advice.

## Project structure

```text
.
├── app.py                  # Premium mobile Streamlit UI and session workflow
├── portfolio_analytics.py  # Portfolio analytics, alerts, and AI scoring rubric
├── coingecko.py            # Public CoinGecko client
├── portfolio_io.py         # Editable portfolio schema and offline CSV import
├── sample_data.py          # Legacy compatibility wrapper returning an empty portfolio
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

No secrets are required because the app does not use private keys, exchange APIs, or trading credentials.

## Usage notes

1. Add CoinGecko IDs in the sidebar, such as `bitcoin`, `ethereum`, or `solana`.
2. Add holdings manually or import an offline Spot CSV snapshot.
3. Mark favorites and maintain a watchlist.
4. Review portfolio performance, market cards, alerts, and AI Intelligence scores.
5. Export your portfolio CSV if you want to save your local session data.

## Educational-only disclaimer

Trader AI does not provide financial, investment, legal, or tax advice. Opportunity scores and explanations are educational research tools only and are not buy, sell, or hold recommendations.
