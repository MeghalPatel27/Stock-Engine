"""Validate RankRow frames before publish."""

from __future__ import annotations

import math

import pandas as pd

RANK_COLUMNS = (
    "symbol",
    "isin",
    "as_of_date",
    "session_date",
    "horizon",
    "p_bullish",
    "p_bearish",
    "p_neutral",
    "risk",
    "confidence",
    "score_long",
    "score_short",
    "rank_long",
    "rank_short",
    "model_version",
    "config_version",
)


def validate_rank_frame(frame: pd.DataFrame, *, horizon: int, model_version: str) -> list[str]:
    errors: list[str] = []
    for col in RANK_COLUMNS:
        if col not in frame.columns:
            errors.append(f"missing column {col}")
    if errors:
        return errors
    if frame.empty:
        errors.append("empty rank frame")
        return errors

    key = ["isin", "session_date", "horizon", "model_version"]
    dup = frame.duplicated(subset=key, keep=False)
    if bool(dup.any()):
        errors.append(f"duplicate keys {key}: {int(dup.sum())} rows involved")

    if not (frame["horizon"] == horizon).all():
        errors.append("horizon mismatch")
    if not (frame["model_version"] == model_version).all():
        errors.append("model_version mismatch")

    for col in ("p_bullish", "p_bearish", "risk", "confidence"):
        vals = pd.to_numeric(frame[col], errors="coerce")
        if vals.isna().any() or ((vals < 0) | (vals > 1)).any():
            errors.append(f"{col} must be finite in [0, 1]")
        if any(not math.isfinite(float(x)) for x in vals):
            errors.append(f"non-finite {col}")

    n = len(frame)
    if set(frame["rank_long"].astype(int)) != set(range(1, n + 1)):
        errors.append("rank_long must be a permutation of 1..n")
    if set(frame["rank_short"].astype(int)) != set(range(1, n + 1)):
        errors.append("rank_short must be a permutation of 1..n")

    leak = {"label", "forward_return", "y_bullish", "y_bearish"} & set(frame.columns)
    if leak:
        errors.append(f"label columns must not appear in ranks: {sorted(leak)}")

    return errors
