"""Momentum simple returns on adjusted close (trading-session lookbacks)."""

from __future__ import annotations

from stock_engine.features.compute.common import rolling_simple_return
from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.models import FeatureSpec

UPSTREAM_ID = "raw__close_adj__l1@v1"
UPSTREAM_COL = "raw__close_adj__l1"


def _ret(ctx: ComputeContext, spec: FeatureSpec, periods: int):
    return rolling_simple_return(
        ctx,
        spec,
        upstream_id=UPSTREAM_ID,
        upstream_col=UPSTREAM_COL,
        periods=periods,
    )


def compute_mom_ret_1d(ctx: ComputeContext, spec: FeatureSpec):
    return _ret(ctx, spec, 1)


def compute_mom_ret_5d(ctx: ComputeContext, spec: FeatureSpec):
    return _ret(ctx, spec, 5)


def compute_mom_ret_20d(ctx: ComputeContext, spec: FeatureSpec):
    return _ret(ctx, spec, 20)


def compute_mom_ret_60d(ctx: ComputeContext, spec: FeatureSpec):
    return _ret(ctx, spec, 60)
