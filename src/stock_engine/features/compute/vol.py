"""Volatility family: realized std of returns."""

from __future__ import annotations

from stock_engine.features.compute.common import rolling_std
from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.models import FeatureSpec

RET_ID = "mom__ret__1d@v1"
RET_COL = "mom__ret__1d"


def compute_vol_std_20d(ctx: ComputeContext, spec: FeatureSpec):
    return rolling_std(ctx, spec, upstream_id=RET_ID, upstream_col=RET_COL, window=20)


def compute_vol_std_60d(ctx: ComputeContext, spec: FeatureSpec):
    return rolling_std(ctx, spec, upstream_id=RET_ID, upstream_col=RET_COL, window=60)
