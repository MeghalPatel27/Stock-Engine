"""Tests for trend__rsi__14 and MACD family."""

from __future__ import annotations

import pandas as pd

from stock_engine.features.compute.indicators import (
    compute_trend_macd_12_26_9,
    compute_trend_macd_hist_12_26_9,
    compute_trend_macd_signal_12_26_9,
    compute_trend_rsi_14,
)
from stock_engine.features.compute.raw_close_adj import compute_raw_close_adj_l1
from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.registry import load_registry
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _registry():
    return load_registry(
        REPO / "docs" / "features" / "registry",
        REPO / "docs" / "features" / "families.yaml",
        datasets_path=REPO / "docs" / "features" / "datasets.yaml",
    )


def _ctx(closes: list[float]) -> ComputeContext:
    n = len(closes)
    sessions = pd.DatetimeIndex(pd.date_range("2026-01-02", periods=n, freq="B"))
    l1 = pd.DataFrame(
        {
            "isin": ["INE001"] * n,
            "session_date": sessions,
            "close_adj": closes,
        }
    )
    return ComputeContext(
        as_of_date=sessions[-1].date(),
        l1_equity=l1,
        open_sessions=sessions,
    )


def test_rsi_14_monotonic_up() -> None:
    registry = _registry()
    ctx = _ctx([100.0 + i for i in range(30)])
    ctx.features["raw__close_adj__l1@v1"] = compute_raw_close_adj_l1(
        ctx, registry.get("raw__close_adj__l1", "v1")
    )
    out = compute_trend_rsi_14(ctx, registry.get("trend__rsi__14", "v1"))
    last = out.dropna().iloc[-1]["trend__rsi__14"]
    assert float(last) == 100.0


def test_macd_hist_equals_line_minus_signal() -> None:
    registry = _registry()
    ctx = _ctx([100.0 + 0.5 * i + (i % 3) for i in range(60)])
    ctx.features["raw__close_adj__l1@v1"] = compute_raw_close_adj_l1(
        ctx, registry.get("raw__close_adj__l1", "v1")
    )
    macd = compute_trend_macd_12_26_9(ctx, registry.get("trend__macd__12_26_9", "v1"))
    ctx.features["trend__macd__12_26_9@v1"] = macd
    signal = compute_trend_macd_signal_12_26_9(
        ctx, registry.get("trend__macd_signal__12_26_9", "v1")
    )
    ctx.features["trend__macd_signal__12_26_9@v1"] = signal
    hist = compute_trend_macd_hist_12_26_9(
        ctx, registry.get("trend__macd_hist__12_26_9", "v1")
    )
    m = macd.merge(signal, on=["isin", "session_date"]).merge(
        hist, on=["isin", "session_date"]
    )
    m = m.dropna()
    assert not m.empty
    diff = m["trend__macd__12_26_9"] - m["trend__macd_signal__12_26_9"]
    assert (m["trend__macd_hist__12_26_9"] - diff).abs().max() < 1e-10


def test_rsi_bounded_0_100() -> None:
    registry = _registry()
    # alternating up/down
    closes = [100.0]
    for i in range(1, 40):
        closes.append(closes[-1] * (1.02 if i % 2 else 0.98))
    ctx = _ctx(closes)
    ctx.features["raw__close_adj__l1@v1"] = compute_raw_close_adj_l1(
        ctx, registry.get("raw__close_adj__l1", "v1")
    )
    out = compute_trend_rsi_14(ctx, registry.get("trend__rsi__14", "v1"))
    valid = out["trend__rsi__14"].dropna()
    assert valid.min() >= 0.0
    assert valid.max() <= 100.0
