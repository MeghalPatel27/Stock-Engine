"""Shared helpers for feature computers."""

from __future__ import annotations

import pandas as pd

from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.inputs import apply_pit_filter
from stock_engine.features.models import FeatureSpec


def require_upstream(
    ctx: ComputeContext, feature_id: str, column: str, spec: FeatureSpec
) -> pd.DataFrame:
    if feature_id not in ctx.features:
        msg = f"{spec.feature_id}: missing upstream feature {feature_id}"
        raise ValueError(msg)
    frame = ctx.features[feature_id]
    if column not in frame.columns:
        msg = f"{spec.feature_id}: upstream {feature_id} missing column {column}"
        raise ValueError(msg)
    out = frame[["isin", "session_date", column]].copy()
    out["session_date"] = pd.to_datetime(out["session_date"]).dt.normalize()
    open_set = set(ctx.open_sessions)
    out = out.loc[out["session_date"].isin(open_set)].copy()
    if out.empty:
        msg = f"{spec.feature_id}: no open-session rows after calendar filter"
        raise ValueError(msg)
    return out.sort_values(["isin", "session_date"]).reset_index(drop=True)


def project_l1_column(
    ctx: ComputeContext,
    spec: FeatureSpec,
    *,
    source_col: str,
    require_positive: bool = False,
) -> pd.DataFrame:
    if source_col not in ctx.l1_equity.columns:
        msg = f"{spec.feature_id}: L1 missing column {source_col}"
        raise ValueError(msg)
    src = apply_pit_filter(ctx.l1_equity, ctx.as_of_date)
    if src.empty:
        msg = f"{spec.feature_id}: no L1 rows on or before {ctx.as_of_date.isoformat()}"
        raise ValueError(msg)
    values = pd.to_numeric(src[source_col], errors="coerce")
    if bool(values.isna().any()):
        msg = f"{spec.feature_id}: null/non-numeric {source_col} (null_policy=fail_run)"
        raise ValueError(msg)
    if require_positive and bool((values <= 0).any()):
        msg = f"{spec.feature_id}: non-positive {source_col} values"
        raise ValueError(msg)
    return (
        pd.DataFrame(
            {
                "isin": src["isin"].astype(str),
                "session_date": pd.to_datetime(src["session_date"]).dt.normalize(),
                spec.name: values.astype(float),
            }
        )
        .sort_values(["isin", "session_date"])
        .reset_index(drop=True)
    )


def rolling_simple_return(
    ctx: ComputeContext,
    spec: FeatureSpec,
    *,
    upstream_id: str,
    upstream_col: str,
    periods: int,
) -> pd.DataFrame:
    src = require_upstream(ctx, upstream_id, upstream_col, spec)
    close = pd.to_numeric(src[upstream_col], errors="coerce")
    ret = close.groupby(src["isin"], sort=False).pct_change(periods=periods)
    return (
        pd.DataFrame(
            {
                "isin": src["isin"].astype(str),
                "session_date": src["session_date"],
                spec.name: ret.astype(float),
            }
        )
        .sort_values(["isin", "session_date"])
        .reset_index(drop=True)
    )


def rolling_mean(
    ctx: ComputeContext,
    spec: FeatureSpec,
    *,
    upstream_id: str,
    upstream_col: str,
    window: int,
) -> pd.DataFrame:
    src = require_upstream(ctx, upstream_id, upstream_col, spec)
    values = pd.to_numeric(src[upstream_col], errors="coerce")
    rolled = values.groupby(src["isin"], sort=False).transform(
        lambda s: s.rolling(window=window, min_periods=window).mean()
    )
    return (
        pd.DataFrame(
            {
                "isin": src["isin"].astype(str),
                "session_date": src["session_date"],
                spec.name: rolled.astype(float),
            }
        )
        .sort_values(["isin", "session_date"])
        .reset_index(drop=True)
    )


def rolling_std(
    ctx: ComputeContext,
    spec: FeatureSpec,
    *,
    upstream_id: str,
    upstream_col: str,
    window: int,
) -> pd.DataFrame:
    src = require_upstream(ctx, upstream_id, upstream_col, spec)
    values = pd.to_numeric(src[upstream_col], errors="coerce")
    rolled = values.groupby(src["isin"], sort=False).transform(
        lambda s: s.rolling(window=window, min_periods=window).std(ddof=0)
    )
    return (
        pd.DataFrame(
            {
                "isin": src["isin"].astype(str),
                "session_date": src["session_date"],
                spec.name: rolled.astype(float),
            }
        )
        .sort_values(["isin", "session_date"])
        .reset_index(drop=True)
    )


def ewm_mean(
    ctx: ComputeContext,
    spec: FeatureSpec,
    *,
    upstream_id: str,
    upstream_col: str,
    span: int,
) -> pd.DataFrame:
    src = require_upstream(ctx, upstream_id, upstream_col, spec)
    values = pd.to_numeric(src[upstream_col], errors="coerce")
    rolled = values.groupby(src["isin"], sort=False).transform(
        lambda s: s.ewm(span=span, adjust=False, min_periods=span).mean()
    )
    return (
        pd.DataFrame(
            {
                "isin": src["isin"].astype(str),
                "session_date": src["session_date"],
                spec.name: rolled.astype(float),
            }
        )
        .sort_values(["isin", "session_date"])
        .reset_index(drop=True)
    )


def sma_mean(
    ctx: ComputeContext,
    spec: FeatureSpec,
    *,
    upstream_id: str,
    upstream_col: str,
    window: int,
) -> pd.DataFrame:
    return rolling_mean(
        ctx, spec, upstream_id=upstream_id, upstream_col=upstream_col, window=window
    )


def merge_two_features(
    left: pd.DataFrame,
    right: pd.DataFrame,
    left_col: str,
    right_col: str,
) -> pd.DataFrame:
    out = left[["isin", "session_date", left_col]].merge(
        right[["isin", "session_date", right_col]],
        on=["isin", "session_date"],
        how="inner",
        validate="one_to_one",
    )
    return out.sort_values(["isin", "session_date"]).reset_index(drop=True)


def cross_section_zscore(frame: pd.DataFrame, value_col: str, out_col: str) -> pd.DataFrame:
    """Z-score within each session_date across ISINs (ddof=0). Null inputs stay null."""
    src = frame[["isin", "session_date", value_col]].copy()
    src["session_date"] = pd.to_datetime(src["session_date"]).dt.normalize()

    def _z(s: pd.Series) -> pd.Series:
        valid = s.dropna()
        if len(valid) == 0:
            return s * float("nan")
        mu = float(valid.mean())
        sigma = float(valid.std(ddof=0))
        if sigma == 0.0 or pd.isna(sigma):
            out = s.copy()
            out.loc[s.notna()] = 0.0
            return out
        return (s - mu) / sigma

    src[out_col] = src.groupby("session_date", sort=False)[value_col].transform(_z)
    return (
        src[["isin", "session_date", out_col]]
        .sort_values(["isin", "session_date"])
        .reset_index(drop=True)
    )


def cross_section_rank(frame: pd.DataFrame, value_col: str, out_col: str) -> pd.DataFrame:
    """Percentile rank within each session_date (average ties), in [0, 1]."""
    src = frame[["isin", "session_date", value_col]].copy()
    src["session_date"] = pd.to_datetime(src["session_date"]).dt.normalize()
    src[out_col] = src.groupby("session_date", sort=False)[value_col].rank(
        method="average", pct=True
    )
    return (
        src[["isin", "session_date", out_col]]
        .sort_values(["isin", "session_date"])
        .reset_index(drop=True)
    )
