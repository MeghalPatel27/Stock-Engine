"""Heuristic risk / confidence composites (ADR-01 components; V1 weights simple)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def heuristic_risk(features: pd.DataFrame) -> pd.Series:
    """
    Map available vol/liquidity features into risk in [0, 1].

    Uses cross-sectional ranks when columns exist; otherwise constant 0.5.
    """
    n = len(features)
    if n == 0:
        return pd.Series(dtype=float)

    parts: list[pd.Series] = []
    for col in ("vol__std__20d", "vol__std__60d"):
        if col in features.columns:
            s = pd.to_numeric(features[col], errors="coerce")
            # higher vol → higher risk
            parts.append(s.rank(pct=True, method="average").fillna(0.5))
    for col in ("liq__adv__20d", "liq__adv__60d"):
        if col in features.columns:
            s = pd.to_numeric(features[col], errors="coerce")
            # lower ADV → higher risk
            parts.append((1.0 - s.rank(pct=True, method="average")).fillna(0.5))

    if not parts:
        return pd.Series(np.full(n, 0.5), index=features.index, dtype=float)

    risk = sum(parts) / len(parts)
    return risk.clip(0.0, 1.0)


def heuristic_confidence(
    p_bullish: pd.Series | np.ndarray,
    p_bearish: pd.Series | np.ndarray,
) -> pd.Series:
    """
    Simple margin-based confidence in [0, 1].

    Not equal to max(p_bullish, p_bearish) alone — uses directional margin.
    """
    pb = pd.Series(np.asarray(p_bullish, dtype=float))
    ps = pd.Series(np.asarray(p_bearish, dtype=float))
    margin = (pb - ps).abs()
    # Blend margin with strength of the dominant head
    strength = pd.concat([pb, ps], axis=1).max(axis=1)
    conf = (0.5 * margin + 0.5 * strength).clip(0.0, 1.0)
    conf.index = pb.index
    return conf
