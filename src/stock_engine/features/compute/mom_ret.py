"""mom__ret__1d — one-session simple return on adjusted close."""

from __future__ import annotations

import pandas as pd

from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.models import FeatureSpec

UPSTREAM_ID = "raw__close_adj__l1@v1"
UPSTREAM_COL = "raw__close_adj__l1"


def compute_mom_ret_1d(ctx: ComputeContext, spec: FeatureSpec) -> pd.DataFrame:
    """
    Compute close[T] / close[T-1] - 1 on open trading sessions only.

    Insufficient lookback (first open session per ISIN) → NaN (null_policy=propagate).
    """
    if UPSTREAM_ID not in ctx.features:
        msg = f"{spec.feature_id}: missing upstream feature {UPSTREAM_ID}"
        raise ValueError(msg)

    upstream = ctx.features[UPSTREAM_ID]
    if UPSTREAM_COL not in upstream.columns:
        msg = f"{spec.feature_id}: upstream missing column {UPSTREAM_COL}"
        raise ValueError(msg)

    src = upstream[["isin", "session_date", UPSTREAM_COL]].copy()
    src["session_date"] = pd.to_datetime(src["session_date"]).dt.normalize()
    open_set = set(ctx.open_sessions)
    src = src.loc[src["session_date"].isin(open_set)].copy()
    if src.empty:
        msg = f"{spec.feature_id}: no open-session rows after calendar filter"
        raise ValueError(msg)

    src = src.sort_values(["isin", "session_date"]).reset_index(drop=True)
    close = pd.to_numeric(src[UPSTREAM_COL], errors="coerce")
    # Groupby pct_change uses prior row in sorted open-session series (= prior open day)
    ret = close.groupby(src["isin"], sort=False).pct_change(periods=1)

    out = pd.DataFrame(
        {
            "isin": src["isin"].astype(str),
            "session_date": src["session_date"],
            spec.name: ret.astype(float),
        }
    )
    return out.sort_values(["isin", "session_date"]).reset_index(drop=True)
