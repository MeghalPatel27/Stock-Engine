"""Label assignment unit tests."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from stock_engine.features.calendar import session_after
from stock_engine.labels.compute import (
    assign_labels,
    compute_forward_returns,
    validate_label_frame,
)


def test_session_after() -> None:
    cal = pd.DatetimeIndex(pd.to_datetime(["2026-07-14", "2026-07-15", "2026-07-16", "2026-07-17"]))
    assert session_after(cal, date(2026, 7, 14), offset=2) == pd.Timestamp("2026-07-16")
    assert session_after(cal, date(2026, 7, 16), offset=5) is None


def test_assign_labels_counts_and_quantiles_embedded() -> None:
    # 10 names, returns 0..9 → top 20% floor = 2 bullish, bottom 2 bearish
    rows = [
        {
            "isin": f"INE{i:03d}",
            "session_date": pd.Timestamp("2026-07-10"),
            "forward_return": float(i),
        }
        for i in range(10)
    ]
    forward = pd.DataFrame(rows)
    out = assign_labels(
        forward,
        horizon=5,
        top_quantile=0.20,
        bottom_quantile=0.20,
        selection_policy="floor",
        universe_mode="pilot",
        label_version="v1",
        label_source="price_return_v1",
    )
    assert len(out) == 10
    assert (out["top_quantile"] == 0.20).all()
    assert (out["bottom_quantile"] == 0.20).all()
    assert (out["label"] == "bullish").sum() == 2
    assert (out["label"] == "bearish").sum() == 2
    assert (out["label"] == "neutral").sum() == 6
    # Highest returns bullish
    bulls = set(out.loc[out["label"] == "bullish", "isin"])
    assert bulls == {"INE008", "INE009"}
    bears = set(out.loc[out["label"] == "bearish", "isin"])
    assert bears == {"INE000", "INE001"}
    assert validate_label_frame(out, horizon=5, label_version="v1") == []


def test_bearish_tie_break_prefers_smaller_isin() -> None:
    """Bearish uses (R asc, isin asc) — not the tail of a desc sort."""
    forward = pd.DataFrame(
        {
            "isin": ["INE002", "INE001", "INE000", "INE003", "INE004"],
            "session_date": [pd.Timestamp("2026-07-10")] * 5,
            # Two names tied at the bottom return
            "forward_return": [0.0, 0.0, 0.1, 0.2, 0.3],
        }
    )
    out = assign_labels(
        forward,
        horizon=5,
        top_quantile=0.20,
        bottom_quantile=0.20,
        selection_policy="floor",
        universe_mode="l1_intersection",
        label_version="v1",
        label_source="price_return_v1",
    )
    # floor(5*0.2)=1 bearish among tied 0.0 returns → smaller isin wins
    bears = set(out.loc[out["label"] == "bearish", "isin"])
    assert bears == {"INE001"}
    bulls = set(out.loc[out["label"] == "bullish", "isin"])
    assert bulls == {"INE004"}


def test_ceil_policy_expands_tails() -> None:
    forward = pd.DataFrame(
        {
            "isin": [f"INE{i:03d}" for i in range(5)],
            "session_date": [pd.Timestamp("2026-07-10")] * 5,
            "forward_return": [float(i) for i in range(5)],
        }
    )
    out = assign_labels(
        forward,
        horizon=5,
        top_quantile=0.20,
        bottom_quantile=0.20,
        selection_policy="ceil",
        universe_mode="pilot",
        label_version="v1",
        label_source="price_return_v1",
    )
    # ceil(5*0.2)=1 → still 1/1; with n=11 ceil expands
    assert (out["label"] == "bullish").sum() == 1
    forward11 = pd.DataFrame(
        {
            "isin": [f"INE{i:03d}" for i in range(11)],
            "session_date": [pd.Timestamp("2026-07-10")] * 11,
            "forward_return": [float(i) for i in range(11)],
        }
    )
    out11 = assign_labels(
        forward11,
        horizon=5,
        top_quantile=0.20,
        bottom_quantile=0.20,
        selection_policy="ceil",
        universe_mode="pilot",
        label_version="v1",
        label_source="price_return_v1",
    )
    assert (out11["label"] == "bullish").sum() == 3
    assert (out11["label"] == "bearish").sum() == 3


def test_duplicate_keys_fail_validation() -> None:
    frame = pd.DataFrame(
        {
            "isin": ["INE001", "INE001"],
            "session_date": [pd.Timestamp("2026-07-10")] * 2,
            "horizon": [5, 5],
            "forward_return": [0.1, 0.2],
            "label": ["bullish", "neutral"],
            "universe_size": [2, 2],
            "label_version": ["v1", "v1"],
            "universe_mode": ["pilot", "pilot"],
            "selection_policy": ["floor", "floor"],
            "top_quantile": [0.2, 0.2],
            "bottom_quantile": [0.2, 0.2],
            "sample_weight": [1.0, 1.0],
            "label_source": ["price_return_v1", "price_return_v1"],
        }
    )
    errors = validate_label_frame(frame, horizon=5, label_version="v1")
    assert any("duplicate keys" in e for e in errors)


def test_forward_return_formula() -> None:
    sessions = pd.DatetimeIndex(
        pd.to_datetime(["2026-07-10", "2026-07-11", "2026-07-14", "2026-07-15", "2026-07-16"])
    )
    l1 = pd.DataFrame(
        {
            "isin": ["INE001"] * 5,
            "session_date": sessions,
            "close_adj": [100.0, 101.0, 102.0, 103.0, 110.0],
        }
    )
    fwd = compute_forward_returns(l1, sessions, horizon=2, as_of_date=date(2026, 7, 16))
    # T=2026-07-10 → T+2=2026-07-14 → 102/100-1
    row = fwd[fwd["session_date"] == pd.Timestamp("2026-07-10")].iloc[0]
    assert abs(float(row["forward_return"]) - 0.02) < 1e-12


def test_phase1_filters_not_implemented() -> None:
    forward = pd.DataFrame(
        {
            "isin": ["INE001"],
            "session_date": [pd.Timestamp("2026-07-10")],
            "forward_return": [0.1],
        }
    )
    with pytest.raises(NotImplementedError):
        assign_labels(
            forward,
            horizon=5,
            top_quantile=0.2,
            bottom_quantile=0.2,
            selection_policy="floor",
            universe_mode="phase1_filters",
            label_version="v1",
            label_source="price_return_v1",
        )
