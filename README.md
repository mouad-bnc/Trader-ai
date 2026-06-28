# Trader AI V2

Application Streamlit crypto premium, mobile-first, reconstruite from scratch avec une architecture modulaire légère MVC.

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
