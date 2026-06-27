from __future__ import annotations

from components.ui import render_empty_card


def render_bots(**_ignored_kwargs) -> None:
    render_empty_card("⌘", "Bots", "Aucun bot connecté. Les performances réelles s'afficheront uniquement après connexion d'une source de données.")
