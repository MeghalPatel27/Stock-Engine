"""Per-stock training metrics tests."""

import pandas as pd

from stock_engine.models.metrics import evaluate_stock_series_predictions


def test_stock_series_metrics() -> None:
    pred = pd.DataFrame(
        {
            "label": ["bullish", "neutral", "bearish", "bullish"],
            "forward_return": [0.05, 0.0, -0.04, 0.03],
            "p_bullish": [0.8, 0.4, 0.2, 0.7],
            "p_bearish": [0.1, 0.3, 0.75, 0.2],
            "score_long": [0.5, 0.2, 0.1, 0.45],
            "score_short": [0.05, 0.15, 0.5, 0.1],
        }
    )
    m = evaluate_stock_series_predictions(pred)
    assert "auc_bullish" in m
    assert m["n_rows"] == 4.0
