"""Two-head HistGradientBoosting trainers (production-loadable)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier


def default_hgb_params(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    m = cfg or {}
    return {
        "learning_rate": float(m.get("learning_rate", 0.05)),
        "max_depth": int(m.get("max_depth", 4)),
        "max_leaf_nodes": int(m.get("max_leaf_nodes", 31)),
        "min_samples_leaf": int(m.get("min_samples_leaf", 20)),
        "l2_regularization": float(m.get("l2_regularization", 1.0)),
        "random_state": int(m.get("random_seed", 42)),
        "max_iter": int(m.get("max_iter", 100)),
    }


def _fit_one(
    X: np.ndarray,
    y: np.ndarray,
    sample_weight: np.ndarray | None,
    params: dict[str, Any],
) -> HistGradientBoostingClassifier:
    # Need both classes for probability; if single class, fit a stub constant model
    classes = np.unique(y)
    if len(classes) < 2:
        clf = HistGradientBoostingClassifier(**params)
        # Duplicate a tiny epsilon row flip is messy; use constant via wrapping
        # Fit on synthetic two-class nudge for API compatibility
        X2 = np.vstack([X, X[:1]])
        y2 = np.concatenate([y, [1 - int(classes[0]) if len(classes) else 0]])
        w2 = None
        if sample_weight is not None:
            w2 = np.concatenate([sample_weight, sample_weight[:1]])
        clf.fit(X2, y2, sample_weight=w2)
        return clf
    clf = HistGradientBoostingClassifier(**params)
    clf.fit(X, y, sample_weight=sample_weight)
    return clf


def fit_two_heads(
    train: pd.DataFrame,
    feature_columns: list[str],
    *,
    params: dict[str, Any] | None = None,
) -> tuple[HistGradientBoostingClassifier, HistGradientBoostingClassifier]:
    p = default_hgb_params(params)
    X = train[feature_columns].to_numpy(dtype=float)
    # sklearn HGB handles NaN natively
    y_b = train["y_bullish"].to_numpy(dtype=int)
    y_s = train["y_bearish"].to_numpy(dtype=int)
    w = train["sample_weight"].to_numpy(dtype=float) if "sample_weight" in train.columns else None
    bull = _fit_one(X, y_b, w, p)
    bear = _fit_one(X, y_s, w, p)
    return bull, bear


def predict_proba_positive(model: HistGradientBoostingClassifier, X: np.ndarray) -> np.ndarray:
    proba = model.predict_proba(X)
    classes = list(model.classes_)
    if 1 in classes:
        return proba[:, classes.index(1)]
    # Model never saw positive class
    return np.zeros(len(X), dtype=float)
