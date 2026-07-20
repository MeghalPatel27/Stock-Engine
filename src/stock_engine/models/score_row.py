"""Score one row with a loaded artifact."""

from __future__ import annotations

from typing import Any

import pandas as pd

from stock_engine.models.ranking import score_long, score_short
from stock_engine.models.risk_confidence import heuristic_confidence, heuristic_risk
from stock_engine.models.trainer import predict_proba_positive


def score_row(
    row: pd.Series,
    feature_columns: list[str],
    art: dict[str, Any],
    *,
    risk_weight: float,
) -> dict[str, float]:
    X = row[feature_columns].to_numpy(dtype=float).reshape(1, -1)
    p_bull = float(predict_proba_positive(art["bullish_model"], X)[0])
    p_bear = float(predict_proba_positive(art["bearish_model"], X)[0])
    frame = pd.DataFrame([row])
    risk = float(heuristic_risk(frame).iloc[0])
    conf = float(heuristic_confidence([p_bull], [p_bear]).iloc[0])
    s_long = float(score_long(p_bull, conf, risk, risk_weight=risk_weight))
    s_short = float(score_short(p_bear, conf, risk, risk_weight=risk_weight))
    return {
        "p_bullish": p_bull,
        "p_bearish": p_bear,
        "risk": risk,
        "confidence": conf,
        "score_long": s_long,
        "score_short": s_short,
    }
