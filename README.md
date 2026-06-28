# MSH AI-Invest V2

MSH AI-Invest — Your Intelligent Investment Copilot.

Application Streamlit crypto premium, mobile-first, reconstruite from scratch avec une architecture modulaire légère MVC. Le tableau de bord conserve son identité fintech noire et dorée pour fournir une plateforme professionnelle d’intelligence d’investissement.

## Architecture

- `app.py` : initialisation Streamlit, chargement services, navigation et routage uniquement.
- `pages/` : vues indépendantes.
- `services/` : logique métier et intégrations externes isolées.
- `components/` : composants UI réutilisables.
- `utils/` : constantes, cache et helpers typés.

## Lancer

```bash
streamlit run app.py
```

Les intégrations externes sont protégées : l'application affiche des états vides si les API sont indisponibles.


## Secrets Streamlit

Configurez Binance en lecture seule dans les secrets Streamlit. `BINANCE_BASE_URL` est optionnel et revient à `https://api.binance.com` s'il est absent ou invalide. Valeurs acceptées : `https://api.binance.com`, `https://api1.binance.com`, `https://api2.binance.com`, `https://api3.binance.com`, `https://data.binance.com`.

```toml
BINANCE_API_KEY = "votre_api_key"
BINANCE_API_SECRET = "votre_api_secret"
BINANCE_BASE_URL = "https://api1.binance.com"
```

## Branding

- Application name: MSH AI-Invest
- Subtitle: Your Intelligent Investment Copilot
- Home page title: Welcome to MSH AI-Invest
- Home page subtitle: Professional investment intelligence platform
- AI page title: MSH AI-Invest Assistant
- Footer: © 2026 MSH AI-Invest

## Validation

Use these checks after conflict resolution or dependency updates to confirm the Streamlit app still imports and starts successfully:

```bash
python - <<'PY'
import importlib
modules = [
    'app',
    'components.cards',
    'components.charts',
    'components.footer',
    'components.header',
    'components.navigation',
    'components.theme',
    'pages.assistant',
    'pages.bots',
    'pages.calculator',
    'pages.home',
    'pages.markets',
    'pages.news',
    'pages.opportunities',
    'pages.portfolio',
    'services.binance_service',
    'services.coingecko_service',
    'services.news_service',
    'services.portfolio_service',
    'utils.cache',
    'utils.constants',
    'utils.helpers',
]
for name in modules:
    importlib.import_module(name)
    print(f'OK {name}')
PY
```

```bash
timeout 15s streamlit run app.py --server.headless true --server.port 8501 --server.address 127.0.0.1
```
