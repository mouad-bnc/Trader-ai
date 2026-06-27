"""Default manual portfolio values for a useful first-run experience."""

from __future__ import annotations

import pandas as pd


def default_portfolio() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"coin_id": "bitcoin", "quantity": 0.05, "avg_cost": 60000.0},
            {"coin_id": "ethereum", "quantity": 1.2, "avg_cost": 2800.0},
            {"coin_id": "solana", "quantity": 12.0, "avg_cost": 130.0},
        ]
    )
