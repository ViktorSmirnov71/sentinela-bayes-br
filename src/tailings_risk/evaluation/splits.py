"""Validation splits implementing docs/04-methods.md §6.1.

- rolling_origin: time-forward CV with monthly step.
- operator_out:   leave-one-operator-out for generalisation tests.
- retrospective:  hold out specific named failure events.
"""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd


def rolling_origin(
    df: pd.DataFrame, time_col: str = "month", step_months: int = 3, train_min_months: int = 24
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Yield (train_idx, test_idx) by walking forward in time."""
    months = np.sort(df[time_col].unique())
    for k in range(train_min_months, len(months), step_months):
        cutoff = months[k]
        train_mask = df[time_col] < cutoff
        test_mask = df[time_col] == cutoff
        yield np.where(train_mask)[0], np.where(test_mask)[0]


def operator_out(df: pd.DataFrame, operator_col: str = "operator_cnpj"):
    operators = df[operator_col].unique()
    for op in operators:
        test_mask = df[operator_col] == op
        train_mask = ~test_mask
        yield np.where(train_mask)[0], np.where(test_mask)[0]


def retrospective_holdout(df: pd.DataFrame, holdout_ids: list[str], id_col: str = "dam_id"):
    test_mask = df[id_col].isin(holdout_ids)
    train_mask = ~test_mask
    return np.where(train_mask)[0], np.where(test_mask)[0]
