"""Purged walk-forward fold helpers (ADR-07)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class WalkForwardFold:
    fold_id: int
    train_end: pd.Timestamp  # inclusive last allowed train session
    test_start: pd.Timestamp
    test_end: pd.Timestamp  # inclusive


def ordered_sessions(session_dates: pd.Series | pd.DatetimeIndex) -> pd.DatetimeIndex:
    sessions = pd.DatetimeIndex(pd.to_datetime(session_dates)).normalize().unique().sort_values()
    return sessions


def build_expanding_folds(
    sessions: pd.DatetimeIndex,
    *,
    horizon: int,
    embargo_sessions: int,
    min_train_sessions: int,
    test_fold_sessions: int,
    step_sessions: int,
) -> list[WalkForwardFold]:
    """
    Expanding walk-forward with purge+embargo before each test fold.

    Train sessions: all S where S <= test_start - horizon - embargo
    (label window [T, T+H] must not overlap test start; then embargo gap).
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if embargo_sessions < 0:
        raise ValueError("embargo_sessions must be >= 0")
    if min_train_sessions < 1:
        raise ValueError("min_train_sessions must be >= 1")
    if test_fold_sessions < 1 or step_sessions < 1:
        raise ValueError("test_fold_sessions and step_sessions must be >= 1")

    sessions = ordered_sessions(sessions)
    n = len(sessions)
    folds: list[WalkForwardFold] = []
    fold_id = 0
    # First test start index must leave room for min train + purge + embargo
    purge_gap = horizon + embargo_sessions
    i = min_train_sessions + purge_gap
    while i + test_fold_sessions <= n:
        test_start = sessions[i]
        test_end = sessions[i + test_fold_sessions - 1]
        train_end_idx = i - purge_gap - 1
        if train_end_idx < min_train_sessions - 1:
            i += step_sessions
            continue
        train_end = sessions[train_end_idx]
        folds.append(
            WalkForwardFold(
                fold_id=fold_id,
                train_end=pd.Timestamp(train_end),
                test_start=pd.Timestamp(test_start),
                test_end=pd.Timestamp(test_end),
            )
        )
        fold_id += 1
        i += step_sessions
    return folds


def mask_train_fold(session_date: pd.Series, fold: WalkForwardFold) -> pd.Series:
    s = pd.to_datetime(session_date).dt.normalize()
    return s <= fold.train_end


def mask_test_fold(session_date: pd.Series, fold: WalkForwardFold) -> pd.Series:
    s = pd.to_datetime(session_date).dt.normalize()
    return (s >= fold.test_start) & (s <= fold.test_end)
