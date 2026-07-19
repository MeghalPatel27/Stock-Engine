"""Aggregate paper-portfolio metrics."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return float("nan")
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def summarize_returns(
    period_returns: pd.Series,
    *,
    periods_per_year: float = 252.0 / 5.0,
) -> dict[str, float]:
    """
    `period_returns` are non-overlapping H-day book returns (one per decision).

    Default annualization assumes decisions every H=5 sessions → ~50.4 periods/year.
    """
    r = period_returns.dropna().astype(float)
    out: dict[str, float] = {
        "n_periods": float(len(r)),
        "mean_period_return": float(r.mean()) if len(r) else float("nan"),
        "std_period_return": float(r.std(ddof=1)) if len(r) > 1 else float("nan"),
    }
    if len(r) == 0:
        out.update(
            {
                "cagr": float("nan"),
                "ann_vol": float("nan"),
                "sharpe_rf0": float("nan"),
                "max_drawdown": float("nan"),
                "hit_rate": float("nan"),
            }
        )
        return out

    equity = (1.0 + r).cumprod()
    total = float(equity.iloc[-1])
    years = len(r) / periods_per_year
    out["cagr"] = float(total ** (1.0 / years) - 1.0) if years > 0 and total > 0 else float("nan")
    out["ann_vol"] = (
        float(r.std(ddof=1) * math.sqrt(periods_per_year)) if len(r) > 1 else float("nan")
    )
    mu = float(r.mean())
    sig = float(r.std(ddof=1)) if len(r) > 1 else float("nan")
    out["sharpe_rf0"] = (
        float((mu / sig) * math.sqrt(periods_per_year))
        if sig and sig == sig and sig > 0
        else float("nan")
    )
    out["max_drawdown"] = max_drawdown(equity)
    out["hit_rate"] = float((r > 0).mean())
    return out


def mean_finite(values: list[float]) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    return float(arr.mean()) if len(arr) else float("nan")
