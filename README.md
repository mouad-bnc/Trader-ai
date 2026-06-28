# Mouad Capital AI V2

Mouad Capital AI — Your Intelligent Investment Copilot.

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


## Branding

- Application name: Mouad Capital AI
- Subtitle: Your Intelligent Investment Copilot
- Home page title: Welcome to Mouad Capital AI
- Home page subtitle: Professional investment intelligence platform
- AI page title: Mouad Capital AI Assistant
- Footer: © 2026 Mouad Capital AI
