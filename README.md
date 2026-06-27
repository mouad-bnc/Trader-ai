# Trader

Trader est un assistant crypto premium mobile-first en français, inspiré de Binance, TradingView et iOS. L’application reste une base Streamlit existante améliorée : elle utilise CoinGecko pour les marchés publics, peut lire Binance Spot côté serveur si des variables d’environnement sont configurées, et n’exécute jamais d’ordre.

## Fonctionnalités

- Navigation haute fixe optimisée iPhone : Accueil, Marchés, Portefeuille, Bots, Actualités, Calculateur, Opportunités, Trader IA.
- Accueil avec valeur totale, PnL du jour, PnL global, répartition Spot / Earn / Bots, top gain, top perte, Fear & Greed, dominance BTC et mini graphique.
- Portefeuille premium avec allocation, graphique circulaire, actifs, prix actuel, valeur, variation et gain / perte.
- Intégration Binance sécurisée en lecture seule via `BINANCE_API_KEY` et `BINANCE_API_SECRET`, jamais exposées au frontend.
- Marchés avec meilleures hausses, plus fortes baisses, liste de suivi, recherche crypto, Fear & Greed et dominance BTC.
- Actualités avec titre, source, date, résumé IA, tags et mode démonstration.
- Calculateur instantané : prix moyen, DCA, objectif gain, seuil de protection, ROI, ratio risque/rendement et taille de position.
- Bots : Spot, contrats, copie de stratégies, performance, rentabilité, capital et analyse IA.
- Opportunités : score /100, signal, confiance et explication.
- Chat moderne Trader avec suggestions en français.
- Architecture prête pour notifications indicatives.

## Sécurité Binance

Les clés Binance sont lues uniquement côté serveur :

```bash
export BINANCE_API_KEY="..."
export BINANCE_API_SECRET="..."
```

Utilisez une clé Binance avec permissions lecture seule. Trader ne contient aucune route de trading, retrait ou futures. Si les variables sont absentes, l’application affiche : `Connexion Binance non configurée.`

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancement local

```bash
streamlit run app.py
```

Ouvrez ensuite l’URL locale indiquée par Streamlit, généralement `http://localhost:8501`.

## Déploiement Streamlit Cloud

1. Poussez le dépôt sur GitHub.
2. Créez une application Streamlit Cloud depuis le dépôt.
3. Définissez `app.py` comme fichier principal.
4. Ajoutez les secrets Binance seulement si vous voulez la lecture Spot.
5. Déployez avec `requirements.txt`.

## Avertissement

Trader fournit une analyse indicative uniquement. Ce n’est pas un conseil financier, fiscal, légal ou d’investissement.
