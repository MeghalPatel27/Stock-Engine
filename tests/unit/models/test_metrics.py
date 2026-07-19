"""Metric helpers including Precision@20."""

import pandas as pd

from stock_engine.models.metrics import evaluate_fold_predictions, precision_at_k


def test_precision_at_20() -> None:
    # One session, 5 names; top-2 by score should hit 1/2 bullish
    frame = pd.DataFrame(
        {
            "session_date": ["2026-07-10"] * 5,
            "label": ["bullish", "neutral", "neutral", "bearish", "neutral"],
            "forward_return": [0.1, 0.0, 0.01, -0.1, 0.02],
            "score_long": [0.9, 0.8, 0.1, 0.0, 0.2],
            "score_short": [0.0, 0.1, 0.2, 0.9, 0.3],
        }
    )
    p = precision_at_k(frame, score_col="score_long", positive_label="bullish", k=2)
    assert abs(p - 0.5) < 1e-9
    metrics = evaluate_fold_predictions(frame, k=2)
    assert "precision_at_k_long" in metrics
    assert abs(metrics["precision_at_k_long"] - 0.5) < 1e-9
