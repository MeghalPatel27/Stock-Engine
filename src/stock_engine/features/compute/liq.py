"""Liquidity family: average daily traded value."""

from __future__ import annotations

from stock_engine.features.compute.common import rolling_mean
from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.models import FeatureSpec

TV_ID = "raw__traded_value__l1@v1"
TV_COL = "raw__traded_value__l1"


def compute_liq_adv_20d(ctx: ComputeContext, spec: FeatureSpec):
    return rolling_mean(ctx, spec, upstream_id=TV_ID, upstream_col=TV_COL, window=20)


def compute_liq_adv_60d(ctx: ComputeContext, spec: FeatureSpec):
    return rolling_mean(ctx, spec, upstream_id=TV_ID, upstream_col=TV_COL, window=60)
