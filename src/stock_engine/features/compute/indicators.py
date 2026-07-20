"""Classic price indicators derived from adjusted close (RSI, MACD)."""

from __future__ import annotations

import pandas as pd

from stock_engine.features.compute.common import merge_two_features, require_upstream
from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.models import FeatureSpec

CLOSE_ID = "raw__close_adj__l1@v1"
CLOSE_COL = "raw__close_adj__l1"

RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9


def _wilder_rsi(close: pd.Series, *, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.where(avg_loss != 0, 100.0)


def _macd_line(close: pd.Series, *, fast: int, slow: int) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    return ema_fast - ema_slow


def _macd_signal(macd: pd.Series, *, span: int) -> pd.Series:
    return macd.ewm(span=span, adjust=False, min_periods=span).mean()


def _from_close_series(
    close: pd.Series,
    isin: pd.Series,
    session_date: pd.Series,
    spec: FeatureSpec,
    values: pd.Series,
) -> pd.DataFrame:
    del close
    return (
        pd.DataFrame(
            {
                "isin": isin.astype(str),
                "session_date": session_date,
                spec.name: values.astype(float),
            }
        )
        .sort_values(["isin", "session_date"])
        .reset_index(drop=True)
    )


def compute_trend_rsi_14(ctx: ComputeContext, spec: FeatureSpec):
    src = require_upstream(ctx, CLOSE_ID, CLOSE_COL, spec)
    close = pd.to_numeric(src[CLOSE_COL], errors="coerce")
    rsi = close.groupby(src["isin"], sort=False).transform(
        lambda s: _wilder_rsi(s, period=RSI_PERIOD)
    )
    return _from_close_series(close, src["isin"], src["session_date"], spec, rsi)


def compute_trend_macd_12_26_9(ctx: ComputeContext, spec: FeatureSpec):
    src = require_upstream(ctx, CLOSE_ID, CLOSE_COL, spec)
    close = pd.to_numeric(src[CLOSE_COL], errors="coerce")
    macd = close.groupby(src["isin"], sort=False).transform(
        lambda s: _macd_line(s, fast=MACD_FAST, slow=MACD_SLOW)
    )
    return _from_close_series(close, src["isin"], src["session_date"], spec, macd)


def compute_trend_macd_signal_12_26_9(ctx: ComputeContext, spec: FeatureSpec):
    macd = require_upstream(ctx, "trend__macd__12_26_9@v1", "trend__macd__12_26_9", spec)
    values = pd.to_numeric(macd["trend__macd__12_26_9"], errors="coerce")
    signal = values.groupby(macd["isin"], sort=False).transform(
        lambda s: _macd_signal(s, span=MACD_SIGNAL)
    )
    return _from_close_series(values, macd["isin"], macd["session_date"], spec, signal)


def compute_trend_macd_hist_12_26_9(ctx: ComputeContext, spec: FeatureSpec):
    macd = require_upstream(ctx, "trend__macd__12_26_9@v1", "trend__macd__12_26_9", spec)
    sig = require_upstream(ctx, "trend__macd_signal__12_26_9@v1", "trend__macd_signal__12_26_9", spec)
    m = merge_two_features(macd, sig, "trend__macd__12_26_9", "trend__macd_signal__12_26_9")
    hist = m["trend__macd__12_26_9"] - m["trend__macd_signal__12_26_9"]
    return (
        pd.DataFrame(
            {
                "isin": m["isin"].astype(str),
                "session_date": m["session_date"],
                spec.name: hist.astype(float),
            }
        )
        .sort_values(["isin", "session_date"])
        .reset_index(drop=True)
    )
