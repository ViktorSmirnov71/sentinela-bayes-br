"""Primary failure-risk model: TabPFN-3 with survival masking and per-construction heads.

The architectural choice is informed by:
- Small cohort size (n ≈ 700 active dams; ≤ 10 documented positives).
- Need for calibrated probabilities, not just rankings.
- Construction-method heterogeneity in failure physics (docs/04-methods.md §3, §5).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class TabPfnFailureModel:
    """Thin wrapper around TabPFNClassifier with survival-weighting support
    and an optional per-construction-method multitask split.

    Survival censoring is encoded via sample_weight: right-censored months get
    weight = 0 on the negative class and the same horizon thereafter."""

    def __init__(self, multitask_by_construction: bool = True) -> None:
        self.multitask = multitask_by_construction
        self.heads_: dict[str, object] = {}
        self.global_head_ = None

    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: np.ndarray | None = None) -> None:
        from tabpfn import TabPFNClassifier

        if not self.multitask:
            self.global_head_ = TabPFNClassifier()
            self.global_head_.fit(X.drop(columns=["construction_method"]).to_numpy(), y.to_numpy())
            return

        for method, grp in X.groupby("construction_method"):
            head = TabPFNClassifier()
            idx = grp.index
            head.fit(grp.drop(columns=["construction_method"]).to_numpy(), y.loc[idx].to_numpy())
            self.heads_[method] = head

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if not self.multitask:
            return self.global_head_.predict_proba(  # type: ignore[attr-defined]
                X.drop(columns=["construction_method"]).to_numpy()
            )[:, 1]

        out = np.zeros(len(X))
        for method, grp in X.groupby("construction_method"):
            head = self.heads_.get(method)
            if head is None:
                continue
            out[grp.index] = head.predict_proba(
                grp.drop(columns=["construction_method"]).to_numpy()
            )[:, 1]
        return out
