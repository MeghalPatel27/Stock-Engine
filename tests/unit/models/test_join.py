"""Train join tests."""

import pandas as pd
import pytest

from stock_engine.models.join import build_train_matrix


def _feat() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "isin": ["INE001", "INE002", "INE001"],
            "session_date": ["2026-07-10", "2026-07-10", "2026-07-11"],
            "mom__ret__5d": [0.1, -0.1, 0.2],
            "vol__std__20d": [0.02, 0.03, 0.02],
        }
    )


def _lab() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "isin": ["INE001", "INE002", "INE001"],
            "session_date": ["2026-07-10", "2026-07-10", "2026-07-11"],
            "horizon": [5, 5, 5],
            "label": ["bullish", "bearish", "neutral"],
            "forward_return": [0.05, -0.04, 0.0],
            "sample_weight": [1.0, 1.0, 1.0],
            "label_version": ["v1", "v1", "v1"],
            "universe_mode": ["pilot"] * 3,
            "label_source": ["price_return_v1"] * 3,
        }
    )


def test_join_builds_targets() -> None:
    out = build_train_matrix(_feat(), _lab(), feature_columns=["mom__ret__5d", "vol__std__20d"])
    assert len(out) == 3
    assert out.loc[out["isin"] == "INE001", "y_bullish"].iloc[0] == 1
    assert out.loc[out["isin"] == "INE002", "y_bearish"].iloc[0] == 1


def test_rejects_label_leak_in_features() -> None:
    feat = _feat()
    feat["label"] = "bullish"
    with pytest.raises(ValueError, match="label columns"):
        build_train_matrix(feat, _lab())


def test_rejects_empty_join() -> None:
    lab = _lab().iloc[:1].copy()
    lab["session_date"] = "2020-01-01"
    with pytest.raises(ValueError, match="empty training matrix"):
        build_train_matrix(_feat(), lab)


def test_rejects_duplicate_feature_ids() -> None:
    with pytest.raises(ValueError, match="duplicate feature"):
        build_train_matrix(_feat(), _lab(), feature_columns=["mom__ret__5d", "mom__ret__5d"])
