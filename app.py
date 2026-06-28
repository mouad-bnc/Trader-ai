from __future__ import annotations

import streamlit as st

from components.header import render_header
from components.navigation import selected_page
from components.theme import apply_theme
from services.binance_service import BinanceService
from services.coingecko_service import CoinGeckoService
from services.news_service import NewsService
from services.portfolio_service import PortfolioService
from utils.constants import APP_NAME, NAV_ITEMS


def secret_value(key: str) -> str:
    try:
        return str(st.secrets.get(key, ""))
    except Exception:
        return ""

from pages import assistant, bots, calculator, home, markets, news, opportunities, portfolio


def load_services() -> dict[str, object]:
    return {
        "coingecko": CoinGeckoService(),
        "binance": BinanceService(secret_value("BINANCE_API_KEY"), secret_value("BINANCE_API_SECRET")),
        "news": NewsService(),
        "portfolio": PortfolioService(),
    }


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="✦", layout="centered", initial_sidebar_state="collapsed")
    apply_theme()
    services = load_services()
    page = selected_page()
    render_header(page, NAV_ITEMS)
    routes = {"Accueil": home.render, "Marchés": markets.render, "Portefeuille": portfolio.render, "Bots": bots.render, "Actualités": news.render, "Calculateur": calculator.render, "Opportunités": opportunities.render, "Trader IA": assistant.render}
    routes.get(page, home.render)(services)


if __name__ == "__main__":
    main()
