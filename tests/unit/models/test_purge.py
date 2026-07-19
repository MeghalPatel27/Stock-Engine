"""Purge / embargo fold tests."""

import pandas as pd

from stock_engine.models.purge import build_expanding_folds, mask_test_fold, mask_train_fold


def test_train_ends_before_purge_and_embargo() -> None:
    # 100 daily sessions
    sessions = pd.date_range("2020-01-01", periods=100, freq="D")
    folds = build_expanding_folds(
        sessions,
        horizon=5,
        embargo_sessions=5,
        min_train_sessions=20,
        test_fold_sessions=10,
        step_sessions=10,
    )
    assert folds
    fold = folds[0]
    # Gap from train_end to test_start must be >= horizon + embargo sessions
    all_s = list(sessions)
    i_train = all_s.index(fold.train_end)
    i_test = all_s.index(fold.test_start)
    assert i_test - i_train - 1 >= 5 + 5

    frame = pd.DataFrame({"session_date": sessions, "x": range(len(sessions))})
    tr = frame.loc[mask_train_fold(frame["session_date"], fold)]
    te = frame.loc[mask_test_fold(frame["session_date"], fold)]
    assert tr["session_date"].max() == fold.train_end
    assert te["session_date"].min() == fold.test_start
    assert te["session_date"].max() == fold.test_end
    assert set(tr["session_date"]).isdisjoint(set(te["session_date"]))
