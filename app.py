from __future__ import annotations

from types import ModuleType
from typing import Callable

import streamlit as st

from components.footer import render_footer
from components.header import render_header
from components.navigation import selected_page
from components.theme import apply_theme
from services.binance_service import BinanceService
from services.coingecko_service import CoinGeckoService
from services.news_service import NewsService
from services.portfolio_service import PortfolioService
from utils.constants import APP_NAME

from pages import assistant, bots, calculator, home, markets, news, opportunities, portfolio

PageRenderer = Callable[[dict[str, object]], None]

PAGE_MODULES: dict[str, ModuleType] = {
    "Accueil": home,
    "Marchés": markets,
    "Portefeuille": portfolio,
    "Bots": bots,
    "Actualités": news,
    "Calculateur": calculator,
    "Opportunités": opportunities,
    "Assistant AI": assistant,
}


def secret_value(key: str) -> str:
    try:
        return str(st.secrets.get(key, ""))
    except Exception:
        return ""


def page_renderers() -> dict[str, PageRenderer]:
    """Return Streamlit page routes and validate each page exposes render()."""
    routes: dict[str, PageRenderer] = {}
    for page_name, module in PAGE_MODULES.items():
        renderer = getattr(module, "render", None)
        if not callable(renderer):
            module_name = getattr(module, "__name__", page_name)
            raise AttributeError(f"Page module {module_name!r} must define a callable render(services) function.")
        routes[page_name] = renderer
    return routes


def load_services() -> dict[str, object]:
    return {
        "coingecko": CoinGeckoService(),
        "binance": BinanceService(
            secret_value("BINANCE_API_KEY"),
            secret_value("BINANCE_API_SECRET"),
            secret_value("BINANCE_BASE_URL"),
        ),
        "news": NewsService(),
        "portfolio": PortfolioService(),
    }


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="✦", layout="wide", initial_sidebar_state="collapsed")
    apply_theme()
    services = load_services()
    render_header()
    page = selected_page()
    routes = page_renderers()
    routes.get(page, routes["Accueil"])(services)
    render_footer()


if __name__ == "__main__":
    main()
