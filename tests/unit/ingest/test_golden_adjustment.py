"""
Golden benchmark datasets — tiny fixtures that must never change behavior.

If these fail after a pipeline change, either fix a regression or deliberately
bump adjustment_method / schema_version and update goldens with review.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from stock_engine.ingest.adjust import build_l1_equity_eod
from stock_engine.ingest.datasets import ADJUSTMENT_METHOD
from stock_engine.ingest.normalize import normalize_corporate_actions, normalize_equity_eod

GOLDEN = Path(__file__).resolve().parents[2] / "golden" / "adjustment_v1"


def test_golden_l1_matches_committed_snapshot() -> None:
    eq = normalize_equity_eod(pd.read_csv(GOLDEN / "equity_eod.csv"))
    ca = normalize_corporate_actions(pd.read_csv(GOLDEN / "corporate_actions.csv"))
    l1, _ = build_l1_equity_eod(eq, ca)
    expected = pd.read_csv(GOLDEN / "expected_l1.csv")
    # Normalize types for comparison
    got = l1.copy()
    got["session_date"] = pd.to_datetime(got["session_date"]).dt.strftime("%Y-%m-%d")
    for col in ("close_raw", "close_adj", "cumulative_adjustment_factor"):
        got[col] = got[col].astype(float)
        expected[col] = expected[col].astype(float)
    cols = [
        "isin",
        "session_date",
        "close_raw",
        "close_adj",
        "cumulative_adjustment_factor",
        "adjustment_method",
    ]
    pd.testing.assert_frame_equal(
        got[cols].reset_index(drop=True),
        expected[cols].reset_index(drop=True),
        check_dtype=False,
    )
    meta = json.loads((GOLDEN / "meta.json").read_text(encoding="utf-8"))
    assert meta["adjustment_method"] == ADJUSTMENT_METHOD
    assert (got["adjustment_method"] == ADJUSTMENT_METHOD).all()
