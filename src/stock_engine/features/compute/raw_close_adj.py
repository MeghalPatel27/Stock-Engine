"""raw__close_adj__l1 — L1 close_adj projection (no math)."""

from __future__ import annotations

import pandas as pd

from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.inputs import apply_pit_filter
from stock_engine.features.models import FeatureSpec

REQUIRED_COLS = ("isin", "session_date", "close_adj")


def compute_raw_close_adj_l1(ctx: ComputeContext, spec: FeatureSpec) -> pd.DataFrame:
    """
    Project L1 ``close_adj`` into a feature column named ``spec.name``.

    PIT: only rows with session_date <= as_of_date.
    Fail-closed on missing columns or null/non-positive close_adj (null_policy=fail_run).
    """
    l1_equity = ctx.l1_equity
    missing = [c for c in REQUIRED_COLS if c not in l1_equity.columns]
    if missing:
        msg = f"{spec.feature_id}: L1 missing columns {missing}"
        raise ValueError(msg)

    src = apply_pit_filter(l1_equity, ctx.as_of_date)
    if src.empty:
        msg = f"{spec.feature_id}: no L1 rows on or before {ctx.as_of_date.isoformat()}"
        raise ValueError(msg)

    values = pd.to_numeric(src["close_adj"], errors="coerce")
    if bool(values.isna().any()):
        msg = f"{spec.feature_id}: null/non-numeric close_adj (null_policy=fail_run)"
        raise ValueError(msg)
    if bool((values <= 0).any()):
        msg = f"{spec.feature_id}: non-positive close_adj values"
        raise ValueError(msg)

    out = pd.DataFrame(
        {
            "isin": src["isin"].astype(str),
            "session_date": src["session_date"],
            spec.name: values.astype(float),
        }
    )
    return out.sort_values(["isin", "session_date"]).reset_index(drop=True)
