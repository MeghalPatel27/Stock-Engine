"""Trend family: EMA / SMA / derived / composite."""

from __future__ import annotations

import pandas as pd

from stock_engine.features.compute.common import (
    ewm_mean,
    merge_two_features,
    require_upstream,
    sma_mean,
)
from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.models import FeatureSpec

CLOSE_ID = "raw__close_adj__l1@v1"
CLOSE_COL = "raw__close_adj__l1"


def compute_trend_ema_10(ctx: ComputeContext, spec: FeatureSpec):
    return ewm_mean(ctx, spec, upstream_id=CLOSE_ID, upstream_col=CLOSE_COL, span=10)


def compute_trend_ema_20(ctx: ComputeContext, spec: FeatureSpec):
    return ewm_mean(ctx, spec, upstream_id=CLOSE_ID, upstream_col=CLOSE_COL, span=20)


def compute_trend_ema_50(ctx: ComputeContext, spec: FeatureSpec):
    return ewm_mean(ctx, spec, upstream_id=CLOSE_ID, upstream_col=CLOSE_COL, span=50)


def compute_trend_sma_20(ctx: ComputeContext, spec: FeatureSpec):
    return sma_mean(ctx, spec, upstream_id=CLOSE_ID, upstream_col=CLOSE_COL, window=20)


def compute_trend_sma_50(ctx: ComputeContext, spec: FeatureSpec):
    return sma_mean(ctx, spec, upstream_id=CLOSE_ID, upstream_col=CLOSE_COL, window=50)


def compute_trend_price_vs_ema_20(ctx: ComputeContext, spec: FeatureSpec):
    close = require_upstream(ctx, CLOSE_ID, CLOSE_COL, spec)
    ema = require_upstream(ctx, "trend__ema__20@v1", "trend__ema__20", spec)
    m = merge_two_features(close, ema, CLOSE_COL, "trend__ema__20")
    out = (m[CLOSE_COL] / m["trend__ema__20"]) - 1.0
    return (
        pd.DataFrame(
            {
                "isin": m["isin"].astype(str),
                "session_date": m["session_date"],
                spec.name: out.astype(float),
            }
        )
        .sort_values(["isin", "session_date"])
        .reset_index(drop=True)
    )


def compute_trend_ema_spread_10_50(ctx: ComputeContext, spec: FeatureSpec):
    e10 = require_upstream(ctx, "trend__ema__10@v1", "trend__ema__10", spec)
    e50 = require_upstream(ctx, "trend__ema__50@v1", "trend__ema__50", spec)
    m = merge_two_features(e10, e50, "trend__ema__10", "trend__ema__50")
    out = (m["trend__ema__10"] - m["trend__ema__50"]) / m["trend__ema__50"]
    return (
        pd.DataFrame(
            {
                "isin": m["isin"].astype(str),
                "session_date": m["session_date"],
                spec.name: out.astype(float),
            }
        )
        .sort_values(["isin", "session_date"])
        .reset_index(drop=True)
    )


def compute_trend_slope_ema20_5d(ctx: ComputeContext, spec: FeatureSpec):
    ema = require_upstream(ctx, "trend__ema__20@v1", "trend__ema__20", spec)
    values = pd.to_numeric(ema["trend__ema__20"], errors="coerce")
    # ema[T] / ema[T-5] - 1 on open-session series
    slope = values.groupby(ema["isin"], sort=False).pct_change(periods=5)
    return (
        pd.DataFrame(
            {
                "isin": ema["isin"].astype(str),
                "session_date": ema["session_date"],
                spec.name: slope.astype(float),
            }
        )
        .sort_values(["isin", "session_date"])
        .reset_index(drop=True)
    )
