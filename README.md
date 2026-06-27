# Trader AI v1

Mini application web locale pour analyser BTC, SOL, SUI et DOGE via les données publiques Binance Spot.

## Important

- Aucun ordre Binance.
- Aucune clé API.
- Aucun trading automatique.
- Analyse éducative uniquement.

## Installation

Ouvre le dossier dans VS Code, puis lance :

```bash
pip install -r requirements.txt
```

## Lancer l'application web

```bash
streamlit run app.py
```

Ensuite, ton navigateur va ouvrir une page locale du type :

```text
http://localhost:8501
```

## Lancer la version terminal

```bash
python trader_assistant.py
```

## Fonctionnalités v1

- Prix actuel.
- Variation 24h.
- RSI 14 jours.
- Moyenne mobile 20 jours.
- Volatilité 20 jours.
- Score opportunité sur 10.
- Décision claire : renforcer léger, surveiller, attendre, ne rien faire.
- Allocation prudente sur ton budget USDT.

## Prochaines versions possibles

- Lecture portefeuille Binance en lecture seule.
- Alertes Telegram.
- Journal de trading.
- Export Excel.
- Déploiement web privé.
