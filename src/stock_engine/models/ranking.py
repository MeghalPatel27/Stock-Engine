"""Configurable ranking scores (ADR-07)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _clip01(x: pd.Series | np.ndarray | float) -> pd.Series | np.ndarray | float:
    return np.clip(x, 0.0, 1.0)


def score_long(
    p_bullish: pd.Series | np.ndarray | float,
    confidence: pd.Series | np.ndarray | float,
    risk: pd.Series | np.ndarray | float,
    *,
    risk_weight: float = 1.0,
) -> pd.Series | np.ndarray | float:
    """score_long = p_bullish * confidence * (1 - risk_weight * risk)."""
    if risk_weight < 0.0:
        msg = "risk_weight must be >= 0"
        raise ValueError(msg)
    return _clip01(p_bullish) * _clip01(confidence) * (1.0 - float(risk_weight) * _clip01(risk))


def score_short(
    p_bearish: pd.Series | np.ndarray | float,
    confidence: pd.Series | np.ndarray | float,
    risk: pd.Series | np.ndarray | float,
    *,
    risk_weight: float = 1.0,
) -> pd.Series | np.ndarray | float:
    """score_short = p_bearish * confidence * (1 - risk_weight * risk)."""
    if risk_weight < 0.0:
        msg = "risk_weight must be >= 0"
        raise ValueError(msg)
    return _clip01(p_bearish) * _clip01(confidence) * (1.0 - float(risk_weight) * _clip01(risk))


def assign_ranks(scores: pd.Series) -> pd.Series:
    """Dense rank: 1 = highest score. Ties broken by index order via method=first after sort."""
    # rank descending; method=first for determinism after stable sort by isin outside
    return scores.rank(ascending=False, method="first").astype(int)
