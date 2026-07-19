"""Feature compute functions (formulas live here; publisher stays formula-free)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import pandas as pd

from stock_engine.features.compute.raw_close_adj import compute_raw_close_adj_l1
from stock_engine.features.models import FeatureSpec

FeatureComputer = Callable[..., pd.DataFrame]

# feature_id -> computer(l1_equity, *, as_of_date, spec) -> frame
FEATURE_COMPUTERS: dict[str, FeatureComputer] = {
    "raw__close_adj__l1@v1": compute_raw_close_adj_l1,
}


def get_computer(feature_id: str) -> FeatureComputer:
    if feature_id not in FEATURE_COMPUTERS:
        msg = f"No computer registered for {feature_id}"
        raise KeyError(msg)
    return FEATURE_COMPUTERS[feature_id]


def compute_feature(
    feature_id: str,
    *,
    l1_equity: pd.DataFrame,
    as_of_date: date,
    spec: FeatureSpec,
) -> pd.DataFrame:
    return get_computer(feature_id)(l1_equity, as_of_date=as_of_date, spec=spec)
