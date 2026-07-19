"""Walk-forward evaluation metrics (ADR-07)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _cs_spearman(score: pd.Series, target: pd.Series) -> float:
    if len(score) < 3:
        return float("nan")
    return float(score.corr(target, method="spearman"))


def cross_sectional_ic(
    frame: pd.DataFrame,
    *,
    score_col: str,
    target_col: str = "forward_return",
    session_col: str = "session_date",
) -> float:
    """Mean Spearman IC of score vs target across sessions."""
    ics: list[float] = []
    for _, g in frame.groupby(session_col, sort=False):
        ics.append(_cs_spearman(g[score_col], g[target_col]))
    arr = np.asarray(ics, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return float("nan")
    return float(arr.mean())


def top_k_hit_rate(
    frame: pd.DataFrame,
    *,
    score_col: str,
    positive_label: str,
    k: int = 20,
    session_col: str = "session_date",
    label_col: str = "label",
) -> float:
    """
    Mean fraction of top-K by score whose label equals positive_label.
    Same as Precision@K when K names are always selected.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    rates: list[float] = []
    for _, g in frame.groupby(session_col, sort=False):
        g = g.sort_values(score_col, ascending=False, kind="mergesort")
        top = g.head(min(k, len(g)))
        if top.empty:
            continue
        rates.append(float((top[label_col] == positive_label).mean()))
    if not rates:
        return float("nan")
    return float(np.mean(rates))


def precision_at_k(
    frame: pd.DataFrame,
    *,
    score_col: str,
    positive_label: str,
    k: int = 20,
    session_col: str = "session_date",
    label_col: str = "label",
) -> float:
    """Precision@K — alias of top_k_hit_rate for ADR-07 naming."""
    return top_k_hit_rate(
        frame,
        score_col=score_col,
        positive_label=positive_label,
        k=k,
        session_col=session_col,
        label_col=label_col,
    )


def evaluate_fold_predictions(
    pred: pd.DataFrame,
    *,
    k: int = 20,
) -> dict[str, float]:
    """
    pred columns required: session_date, label, forward_return,
    score_long, score_short
    """
    long_ic = cross_sectional_ic(pred, score_col="score_long", target_col="forward_return")
    short_ic = cross_sectional_ic(
        pred.assign(_neg=-pred["forward_return"]),
        score_col="score_short",
        target_col="_neg",
    )
    hit_long = top_k_hit_rate(pred, score_col="score_long", positive_label="bullish", k=k)
    hit_short = top_k_hit_rate(pred, score_col="score_short", positive_label="bearish", k=k)
    prec20_long = precision_at_k(pred, score_col="score_long", positive_label="bullish", k=k)
    prec20_short = precision_at_k(pred, score_col="score_short", positive_label="bearish", k=k)
    return {
        "rank_ic_long": long_ic,
        "rank_ic_short": short_ic,
        "top_k_hit_long": hit_long,
        "top_k_hit_short": hit_short,
        "precision_at_k_long": prec20_long,
        "precision_at_k_short": prec20_short,
        "k": float(k),
        "n_rows": float(len(pred)),
        "n_sessions": float(pred["session_date"].nunique()),
    }
