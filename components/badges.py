from __future__ import annotations


def score_badge(score: int) -> str:
    label = "Excellent" if score >= 75 else "Fort" if score >= 60 else "Neutre" if score >= 45 else "Risque"
    return f"<span class='score-badge'><b>{score}</b><small>{label}</small></span>"
