"""Per-ISIN time-series model training (pilot-quality mode)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from stock_engine.models.metrics import evaluate_stock_series_predictions
from stock_engine.models.purge import (
    build_expanding_folds,
    mask_test_fold,
    mask_train_fold,
    ordered_sessions,
)
from stock_engine.models.trainer import default_hgb_params, fit_two_heads, predict_proba_positive
from stock_engine.models.walkforward import _predict_frame, fit_final


def _auc_safe(y_true: np.ndarray, y_score: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    try:
        return float(roc_auc_score(y_true, y_score))
    except ValueError:
        return float("nan")


def tune_stock_params(
    sub: pd.DataFrame,
    feature_columns: list[str],
    *,
    base_cfg: dict[str, Any],
    val_fraction: float = 0.2,
) -> dict[str, Any]:
    """
    Small grid search on a temporal holdout (last val_fraction of sessions).
    Optimizes mean AUC of bullish + bearish heads.
    """
    sessions = ordered_sessions(sub["session_date"])
    if len(sessions) < 100:
        return default_hgb_params(base_cfg)

    split_at = max(1, int(len(sessions) * (1.0 - val_fraction)))
    train_end = sessions[split_at - 1]
    tr = sub.loc[pd.to_datetime(sub["session_date"]).dt.normalize() <= train_end]
    va = sub.loc[pd.to_datetime(sub["session_date"]).dt.normalize() > train_end]
    if tr.empty or va.empty or len(va) < 20:
        return default_hgb_params(base_cfg)

    grid: list[dict[str, Any]] = []
    for lr in (0.04, 0.06, 0.08):
        for depth in (3, 4, 5):
            for leaf in (10, 15):
                p = default_hgb_params(base_cfg)
                p.update(
                    {
                        "learning_rate": lr,
                        "max_depth": depth,
                        "min_samples_leaf": leaf,
                        "max_iter": int(base_cfg.get("max_iter", 200)),
                    }
                )
                grid.append(p)
                if len(grid) >= 12:
                    break
            if len(grid) >= 12:
                break
        if len(grid) >= 12:
            break

    best_params = default_hgb_params(base_cfg)
    best_score = float("-inf")
    X_va = va[feature_columns].to_numpy(dtype=float)
    y_b = va["y_bullish"].to_numpy(dtype=int)
    y_s = va["y_bearish"].to_numpy(dtype=int)

    for params in grid:
        bull, bear = fit_two_heads(tr, feature_columns, params=params)
        pb = predict_proba_positive(bull, X_va)
        ps = predict_proba_positive(bear, X_va)
        auc_b = _auc_safe(y_b, pb)
        auc_s = _auc_safe(y_s, ps)
        parts = [x for x in (auc_b, auc_s) if x == x]
        if not parts:
            continue
        score = float(np.mean(parts))
        if score > best_score:
            best_score = score
            best_params = params

    best_params["tune_val_score"] = best_score if best_score > float("-inf") else float("nan")
    return best_params


def run_walkforward_stock(
    sub: pd.DataFrame,
    feature_columns: list[str],
    *,
    horizon: int = 5,
    embargo_sessions: int = 5,
    min_train_sessions: int = 252,
    test_fold_sessions: int = 21,
    step_sessions: int = 21,
    risk_weight: float = 1.0,
    model_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Purged expanding WF on a single ISIN time series."""
    sessions = ordered_sessions(sub["session_date"])
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
        tr = sub.loc[mask_train_fold(sub["session_date"], fold)]
        te = sub.loc[mask_test_fold(sub["session_date"], fold)]
        if tr.empty or te.empty:
            continue
        bull, bear = fit_two_heads(tr, feature_columns, params=model_params)
        pred = _predict_frame(te, feature_columns, bull, bear, risk_weight=risk_weight)
        metrics = evaluate_stock_series_predictions(pred)
        metrics["fold_id"] = fold.fold_id
        metrics["n_train"] = int(len(tr))
        fold_reports.append(metrics)

    summary: dict[str, float] = {}
    if fold_reports:
        for key in (
            "auc_bullish",
            "auc_bearish",
            "brier_bullish",
            "brier_bearish",
            "bullish_precision",
            "bearish_precision",
            "return_corr_long",
            "return_corr_short",
        ):
            vals = np.asarray([f[key] for f in fold_reports], dtype=float)
            vals = vals[np.isfinite(vals)]
            summary[f"{key}_mean"] = float(vals.mean()) if len(vals) else float("nan")
            summary[f"{key}_std"] = float(vals.std(ddof=0)) if len(vals) else float("nan")
    summary["n_folds"] = float(len(fold_reports))
    return {"folds": fold_reports, "summary": summary}


def train_one_stock(
    sub: pd.DataFrame,
    feature_columns: list[str],
    *,
    isin: str,
    symbol: str,
    mcfg: dict[str, Any],
    tune: bool = True,
) -> tuple[Any, Any, dict[str, Any], dict[str, Any]]:
    """Tune (optional), walk-forward eval, final fit for one ISIN."""
    params = default_hgb_params(mcfg)
    params["max_iter"] = int(mcfg.get("max_iter", 200))
    if tune:
        params = tune_stock_params(sub, feature_columns, base_cfg=mcfg)

    wf = run_walkforward_stock(
        sub,
        feature_columns,
        horizon=int(mcfg.get("horizon", 5)),
        embargo_sessions=int(mcfg.get("embargo_sessions", 5)),
        min_train_sessions=int(mcfg.get("min_train_sessions", 252)),
        test_fold_sessions=int(mcfg.get("test_fold_sessions", 21)),
        step_sessions=int(mcfg.get("per_stock_step_sessions", mcfg.get("step_sessions", 42))),
        risk_weight=float(mcfg.get("risk_weight", 1.0)),
        model_params=params,
    )
    bull, bear = fit_final(sub, feature_columns, model_params=params)
    manifest = {
        "isin": isin,
        "symbol": symbol,
        "training_mode": "per_stock",
        "n_train_rows": int(len(sub)),
        "n_sessions": int(sub["session_date"].nunique()),
        "params": {k: v for k, v in params.items() if k != "tune_val_score"},
        "tune_val_score": params.get("tune_val_score"),
    }
    return bull, bear, wf, manifest
