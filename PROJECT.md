# MSH AI-Invest — Project Guide

## Vision
MSH AI-Invest est un copilote crypto personnel et non un exchange.
L'application aide l'utilisateur à analyser son portefeuille, comprendre le marché et identifier les opportunités.

## Stack technique
- Framework : Streamlit
- Langage : Python
- Point d'entrée : app.py
- Données marché : CoinGecko
- Portefeuille : Binance API (lecture seule) + import CSV
- Déploiement : Streamlit Cloud

## Principes
- Ne jamais reconstruire l'application depuis zéro.
- Une tâche = un objectif.
- Toujours modifier le minimum de fichiers.
- Toujours conserver une application fonctionnelle.
- Toujours tester avant de terminer.

## Navigation officielle
- Accueil
- Marchés
- Portefeuille
- Bots
- Actualités
- Calculateur
- Opportunités
- Assistant AI

Ne plus utiliser les noms Wallet, News ou IA.

## Règles Binance
- Lecture seule uniquement.
- Utiliser BINANCE_API_KEY et BINANCE_API_SECRET.
- Aucun ordre d'achat, de vente, de retrait ou de futures.
- Les clés API ne doivent jamais être exposées côté interface.

## Priorités
Sprint 1 : Architecture
Sprint 2 : Synchronisation Binance
Sprint 3 : Analyse IA
Sprint 4 : Interface Premium

## Consignes pour Codex
Avant chaque tâche :
1. Lire PROJECT.md.
2. Identifier le fichier exact à modifier.
3. Modifier uniquement ce qui est demandé.
4. Ne jamais refaire toute l'application.
5. Vérifier que le projet compile.
6. Résumer les fichiers modifiés.
