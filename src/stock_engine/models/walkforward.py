"""Expanding purged walk-forward evaluation + final freeze train."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from stock_engine.models.metrics import evaluate_fold_predictions
from stock_engine.models.purge import (
    build_expanding_folds,
    mask_test_fold,
    mask_train_fold,
    ordered_sessions,
)
from stock_engine.models.ranking import score_long, score_short
from stock_engine.models.risk_confidence import heuristic_confidence, heuristic_risk
from stock_engine.models.trainer import fit_two_heads, predict_proba_positive


def _predict_frame(
    frame: pd.DataFrame,
    feature_columns: list[str],
    bullish_model: Any,
    bearish_model: Any,
    *,
    risk_weight: float,
) -> pd.DataFrame:
    X = frame[feature_columns].to_numpy(dtype=float)
    p_bull = predict_proba_positive(bullish_model, X)
    p_bear = predict_proba_positive(bearish_model, X)
    out = frame.copy()
    out["p_bullish"] = p_bull
    out["p_bearish"] = p_bear
    out["risk"] = heuristic_risk(frame).to_numpy()
    out["confidence"] = heuristic_confidence(out["p_bullish"], out["p_bearish"]).to_numpy()
    out["score_long"] = score_long(
        out["p_bullish"], out["confidence"], out["risk"], risk_weight=risk_weight
    )
    out["score_short"] = score_short(
        out["p_bearish"], out["confidence"], out["risk"], risk_weight=risk_weight
    )
    return out


def run_walkforward(
    matrix: pd.DataFrame,
    feature_columns: list[str],
    *,
    horizon: int = 5,
    embargo_sessions: int = 5,
    min_train_sessions: int = 60,
    test_fold_sessions: int = 21,
    step_sessions: int = 21,
    top_k: int = 20,
    risk_weight: float = 1.0,
    model_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return fold metrics + summary. Does not write artifacts."""
    sessions = ordered_sessions(matrix["session_date"])
    folds = build_expanding_folds(
        sessions,
        horizon=horizon,
        embargo_sessions=embargo_sessions,
        min_train_sessions=min_train_sessions,
        test_fold_sessions=test_fold_sessions,
        step_sessions=step_sessions,
    )
    fold_reports: list[dict[str, Any]] = []
    for fold in folds:
        tr = matrix.loc[mask_train_fold(matrix["session_date"], fold)]
        te = matrix.loc[mask_test_fold(matrix["session_date"], fold)]
        if tr.empty or te.empty:
            continue
        bull, bear = fit_two_heads(tr, feature_columns, params=model_params)
        pred = _predict_frame(te, feature_columns, bull, bear, risk_weight=risk_weight)
        metrics = evaluate_fold_predictions(pred, k=top_k)
        metrics["fold_id"] = fold.fold_id
        metrics["train_end"] = str(fold.train_end.date())
        metrics["test_start"] = str(fold.test_start.date())
        metrics["test_end"] = str(fold.test_end.date())
        metrics["n_train"] = int(len(tr))
        fold_reports.append(metrics)

    summary: dict[str, float] = {}
    if fold_reports:
        for key in (
            "rank_ic_long",
            "rank_ic_short",
            "top_k_hit_long",
            "top_k_hit_short",
            "precision_at_k_long",
            "precision_at_k_short",
        ):
            vals = np.asarray([f[key] for f in fold_reports], dtype=float)
            vals = vals[np.isfinite(vals)]
            summary[f"{key}_mean"] = float(vals.mean()) if len(vals) else float("nan")
            summary[f"{key}_std"] = float(vals.std(ddof=0)) if len(vals) else float("nan")
    summary["n_folds"] = float(len(fold_reports))

    return {"folds": fold_reports, "summary": summary}


def fit_final(
    matrix: pd.DataFrame,
    feature_columns: list[str],
    *,
    model_params: dict[str, Any] | None = None,
) -> tuple[Any, Any]:
    """Train on full labeled matrix for freeze (caller applies any final holdout)."""
    if matrix.empty:
        msg = "empty training matrix"
        raise ValueError(msg)
    return fit_two_heads(matrix, feature_columns, params=model_params)
