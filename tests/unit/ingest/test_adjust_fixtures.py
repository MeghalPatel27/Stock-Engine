"""Corporate-action adjustment regression fixtures (permanent)."""

from __future__ import annotations

import pandas as pd
import pytest

from stock_engine.ingest.adjust import build_l1_equity_eod
from stock_engine.ingest.datasets import ADJUSTMENT_METHOD
from stock_engine.ingest.normalize import normalize_corporate_actions, normalize_equity_eod
from stock_engine.ingest.validate import validate_corporate_actions


def _equity(rows: list[tuple]) -> pd.DataFrame:
    """rows: (isin, symbol, session_date, close)"""
    df = pd.DataFrame(rows, columns=["isin", "symbol", "session_date", "close"])
    df["open"] = df["close"]
    df["high"] = df["close"]
    df["low"] = df["close"]
    df["volume"] = 1000
    return normalize_equity_eod(df)


def _ca(rows: list[dict]) -> pd.DataFrame:
    return normalize_corporate_actions(pd.DataFrame(rows))


def test_split_2_for_1() -> None:
    eq = _equity(
        [
            ("INE1", "AAA", "2026-07-16", 200.0),
            ("INE1", "AAA", "2026-07-17", 100.0),  # ex-date / post split
        ]
    )
    ca = _ca(
        [
            {
                "isin": "INE1",
                "ex_date": "2026-07-17",
                "action_type": "split",
                "ratio_num": 1,
                "ratio_den": 2,
                "factor": 0.5,
            }
        ]
    )
    l1, _ = build_l1_equity_eod(eq, ca)
    pre = l1[l1["session_date"] == pd.Timestamp("2026-07-16")].iloc[0]
    post = l1[l1["session_date"] == pd.Timestamp("2026-07-17")].iloc[0]
    assert pre["close_raw"] == 200.0
    assert pre["close_adj"] == 100.0
    assert pre["cumulative_adjustment_factor"] == 0.5
    assert post["close_adj"] == 100.0
    assert post["cumulative_adjustment_factor"] == 1.0
    assert (l1["adjustment_method"] == ADJUSTMENT_METHOD).all()


def test_split_5_for_1() -> None:
    eq = _equity(
        [
            ("INE1", "AAA", "2026-07-16", 500.0),
            ("INE1", "AAA", "2026-07-17", 100.0),
        ]
    )
    ca = _ca(
        [
            {
                "isin": "INE1",
                "ex_date": "2026-07-17",
                "action_type": "split",
                "factor": 0.2,
            }
        ]
    )
    l1, _ = build_l1_equity_eod(eq, ca)
    pre = l1[l1["session_date"] == pd.Timestamp("2026-07-16")].iloc[0]
    assert pre["close_adj"] == pytest.approx(100.0)


def test_bonus_1_for_2() -> None:
    """1:2 bonus → 1 new for 2 old → 3 shares from 2 → factor 2/3."""
    eq = _equity(
        [
            ("INE1", "AAA", "2026-07-16", 150.0),
            ("INE1", "AAA", "2026-07-17", 100.0),
        ]
    )
    ca = _ca(
        [
            {
                "isin": "INE1",
                "ex_date": "2026-07-17",
                "action_type": "bonus",
                "ratio_num": 2,
                "ratio_den": 3,
                "factor": 2 / 3,
            }
        ]
    )
    l1, _ = build_l1_equity_eod(eq, ca)
    pre = l1[l1["session_date"] == pd.Timestamp("2026-07-16")].iloc[0]
    assert pre["close_adj"] == pytest.approx(100.0)


def test_multiple_sequential_corporate_actions() -> None:
    eq = _equity(
        [
            ("INE1", "AAA", "2026-07-14", 400.0),
            ("INE1", "AAA", "2026-07-15", 200.0),  # after first 2:1
            ("INE1", "AAA", "2026-07-16", 100.0),  # after second 2:1
        ]
    )
    ca = _ca(
        [
            {
                "isin": "INE1",
                "ex_date": "2026-07-15",
                "action_type": "split",
                "factor": 0.5,
            },
            {
                "isin": "INE1",
                "ex_date": "2026-07-16",
                "action_type": "split",
                "factor": 0.5,
            },
        ]
    )
    l1, _ = build_l1_equity_eod(eq, ca)
    d14 = l1[l1["session_date"] == pd.Timestamp("2026-07-14")].iloc[0]
    d15 = l1[l1["session_date"] == pd.Timestamp("2026-07-15")].iloc[0]
    d16 = l1[l1["session_date"] == pd.Timestamp("2026-07-16")].iloc[0]
    assert d14["cumulative_adjustment_factor"] == pytest.approx(0.25)
    assert d14["close_adj"] == pytest.approx(100.0)
    assert d15["cumulative_adjustment_factor"] == pytest.approx(0.5)
    assert d15["close_adj"] == pytest.approx(100.0)
    assert d16["cumulative_adjustment_factor"] == pytest.approx(1.0)
    assert d16["close_adj"] == pytest.approx(100.0)


def test_symbol_change_does_not_adjust_prices() -> None:
    eq = _equity(
        [
            ("INE1", "OLD", "2026-07-16", 100.0),
            ("INE1", "NEW", "2026-07-17", 105.0),
        ]
    )
    ca = _ca(
        [
            {
                "isin": "INE1",
                "ex_date": "2026-07-17",
                "action_type": "symbol_change",
                "notes": "rename only",
            }
        ]
    )
    l1, _ = build_l1_equity_eod(eq, ca)
    assert (l1["close_adj"] == l1["close_raw"]).all()
    assert (l1["cumulative_adjustment_factor"] == 1.0).all()


def test_merger_does_not_price_adjust_and_is_exclusion_candidate() -> None:
    """Merger is not a V1 price-return factor; identity/exclusion handled later."""
    eq = _equity(
        [
            ("INE1", "AAA", "2026-07-16", 100.0),
            ("INE1", "AAA", "2026-07-17", 110.0),
        ]
    )
    ca = _ca(
        [
            {
                "isin": "INE1",
                "ex_date": "2026-07-17",
                "action_type": "merger",
                "notes": "exclude from labels later",
            }
        ]
    )
    l1, _ = build_l1_equity_eod(eq, ca)
    assert (l1["close_adj"] == l1["close_raw"]).all()
    # Document exclusion window: ex_date is the merger session
    assert ca.iloc[0]["action_type"] == "merger"
    assert ca.iloc[0]["adjusts_price_return"] is False or not bool(
        ca.iloc[0]["adjusts_price_return"]
    )


def test_missing_factor_on_split_fails_dq() -> None:
    ca = normalize_corporate_actions(
        pd.DataFrame(
            [
                {
                    "isin": "INE1",
                    "ex_date": "2026-07-17",
                    "action_type": "split",
                    # no factor / ratios
                }
            ]
        )
    )
    report = validate_corporate_actions(ca)
    assert report.ok is False
    assert any(i.code == "missing_ca_factor" for i in report.issues)
