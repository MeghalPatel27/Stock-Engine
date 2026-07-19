"""Feature compute functions (formulas live here; publisher stays formula-free)."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.compute.mom_ret import compute_mom_ret_1d
from stock_engine.features.compute.raw_close_adj import compute_raw_close_adj_l1
from stock_engine.features.models import FeatureSpec

FeatureComputer = Callable[[ComputeContext, FeatureSpec], pd.DataFrame]

FEATURE_COMPUTERS: dict[str, FeatureComputer] = {
    "raw__close_adj__l1@v1": compute_raw_close_adj_l1,
    "mom__ret__1d@v1": compute_mom_ret_1d,
}


def get_computer(feature_id: str) -> FeatureComputer:
    if feature_id not in FEATURE_COMPUTERS:
        msg = f"No computer registered for {feature_id}"
        raise KeyError(msg)
    return FEATURE_COMPUTERS[feature_id]


def compute_feature(
    feature_id: str,
    *,
    ctx: ComputeContext,
    spec: FeatureSpec,
) -> pd.DataFrame:
    return get_computer(feature_id)(ctx, spec)
