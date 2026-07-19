"""Ranking formula tests."""

import pandas as pd

from stock_engine.models.ranking import score_long, score_short


def test_risk_weight_scales_penalty() -> None:
    p = pd.Series([1.0, 1.0])
    c = pd.Series([1.0, 1.0])
    r = pd.Series([0.5, 0.5])
    s1 = score_long(p, c, r, risk_weight=1.0)
    s2 = score_long(p, c, r, risk_weight=0.0)
    assert list(s1) == [0.5, 0.5]
    assert list(s2) == [1.0, 1.0]
    assert list(score_short(p, c, r, risk_weight=0.5)) == [0.75, 0.75]
