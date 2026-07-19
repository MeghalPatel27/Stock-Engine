"""Cross-sectional ranks and z-scores (universe = names present that session)."""

from __future__ import annotations

import pandas as pd

from stock_engine.features.compute.common import (
    cross_section_rank,
    cross_section_zscore,
    require_upstream,
)
from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.models import FeatureSpec


def _z(ctx: ComputeContext, spec: FeatureSpec, upstream_id: str, upstream_col: str) -> pd.DataFrame:
    src = require_upstream(ctx, upstream_id, upstream_col, spec)
    return cross_section_zscore(src, upstream_col, spec.name)


def _rank(
    ctx: ComputeContext, spec: FeatureSpec, upstream_id: str, upstream_col: str
) -> pd.DataFrame:
    src = require_upstream(ctx, upstream_id, upstream_col, spec)
    return cross_section_rank(src, upstream_col, spec.name)


def compute_cs_zscore_mom_ret_5d(ctx: ComputeContext, spec: FeatureSpec) -> pd.DataFrame:
    return _z(ctx, spec, "mom__ret__5d@v1", "mom__ret__5d")


def compute_cs_zscore_mom_ret_20d(ctx: ComputeContext, spec: FeatureSpec) -> pd.DataFrame:
    return _z(ctx, spec, "mom__ret__20d@v1", "mom__ret__20d")


def compute_cs_rank_mom_ret_5d(ctx: ComputeContext, spec: FeatureSpec) -> pd.DataFrame:
    return _rank(ctx, spec, "mom__ret__5d@v1", "mom__ret__5d")


def compute_cs_zscore_vol_std_20d(ctx: ComputeContext, spec: FeatureSpec) -> pd.DataFrame:
    return _z(ctx, spec, "vol__std__20d@v1", "vol__std__20d")


def compute_cs_zscore_liq_adv_20d(ctx: ComputeContext, spec: FeatureSpec) -> pd.DataFrame:
    return _z(ctx, spec, "liq__adv__20d@v1", "liq__adv__20d")


def compute_cs_zscore_trend_price_vs_ema_20(ctx: ComputeContext, spec: FeatureSpec) -> pd.DataFrame:
    return _z(ctx, spec, "trend__price_vs_ema__20@v1", "trend__price_vs_ema__20")
