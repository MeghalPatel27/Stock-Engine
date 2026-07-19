"""Ingest + L0/L1 cleaning tests."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.ingest.adjust import build_l1_equity_eod
from stock_engine.ingest.local_csv import LocalIncomingCsvSource
from stock_engine.ingest.normalize import normalize_corporate_actions, normalize_equity_eod
from stock_engine.ingest.pipeline import run_ingest
from stock_engine.ingest.raw_store import sha256_file

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "incoming"

ALL = [
    "equity_eod.csv",
    "corporate_actions.csv",
    "symbol_isin_map.csv",
    "trading_calendar.csv",
]


def _stage(tmp_path: Path, names: list[str]) -> Path:
    root = tmp_path / "data"
    incoming = root / "incoming"
    incoming.mkdir(parents=True)
    for name in names:
        shutil.copy(FIXTURES / name, incoming / name)
    for sub in ("raw", "clean", "metadata"):
        (root / sub).mkdir()
    return root


def test_local_source_lists_calendar(tmp_path: Path) -> None:
    root = _stage(tmp_path, ALL)
    arts = LocalIncomingCsvSource(root / "incoming").list_artifacts()
    assert "trading_calendar" in {a.dataset for a in arts}


def test_ingest_publishes_l0_and_l1(tmp_path: Path) -> None:
    root = _stage(tmp_path, ALL)
    result = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert result.status == "success", result.errors
    assert list((root / "clean" / "l0" / "equity_eod").rglob("*.parquet"))
    l1 = list((root / "clean" / "l1" / "equity_eod").rglob("*.parquet"))
    assert len(l1) == 1
    df = pd.read_parquet(l1[0])
    assert "close_adj" in df.columns and "close_raw" in df.columns
    assert "raw_sha256" in df.columns and "schema_version" in df.columns
    # Pre-split day should be half of raw after backward adj (factor 0.5)
    sess = pd.to_datetime(df["session_date"]).dt.normalize()
    pre = df[(df["isin"] == "INE002A01018") & (sess == pd.Timestamp("2026-07-17"))]
    assert len(pre) == 1
    assert float(pre["close_raw"].iloc[0]) == 2880
    assert float(pre["close_adj"].iloc[0]) == 1440


def test_dividend_does_not_adjust_prices(tmp_path: Path) -> None:
    eq = normalize_equity_eod(pd.read_csv(FIXTURES / "equity_eod.csv"))
    ca = normalize_corporate_actions(pd.read_csv(FIXTURES / "corporate_actions.csv"))
    l1, _ = build_l1_equity_eod(eq, ca)
    tcs = l1[l1["isin"] == "INE467B01029"].sort_values("session_date")
    # No split factor for TCS → adj == raw
    assert (tcs["close_adj"] == tcs["close_raw"]).all()


def test_missing_calendar_fails(tmp_path: Path) -> None:
    root = _stage(tmp_path, ["equity_eod.csv", "corporate_actions.csv"])
    result = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert result.status == "failed"
    assert any("trading_calendar" in e for e in result.errors)
    assert list((root / "clean" / "l1").rglob("*.parquet")) == []


def test_missing_recent_session_fails(tmp_path: Path) -> None:
    root = _stage(tmp_path, ALL)
    # Drop 2026-07-18 rows for RELIANCE only — still in calendar
    eq_path = root / "incoming" / "equity_eod.csv"
    df = pd.read_csv(eq_path)
    df = df[~((df["isin"] == "INE002A01018") & (df["session_date"] == "2026-07-18"))]
    df.to_csv(eq_path, index=False)
    result = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert result.status == "failed"
    assert any("missing_recent_sessions" in e for e in result.errors)


def test_deterministic_rebuild(tmp_path: Path) -> None:
    root = _stage(tmp_path, ALL)
    r1 = run_ingest(data_root=root, as_of_date=date(2026, 7, 18), dataset_version="vtest")
    p1 = next((root / "clean" / "l1" / "equity_eod").rglob("*.parquet"))
    df1 = pd.read_parquet(p1)
    # Second run same inputs
    r2 = run_ingest(data_root=root, as_of_date=date(2026, 7, 18), dataset_version="vtest")
    p2 = next((root / "clean" / "l1" / "equity_eod").rglob("*.parquet"))
    df2 = pd.read_parquet(p2)
    assert r1.status == r2.status == "success"
    cols = [c for c in df1.columns if c not in {"ingested_at", "run_id"}]
    pd.testing.assert_frame_equal(df1[cols], df2[cols], check_dtype=False)


def test_raw_checksum_stable(tmp_path: Path) -> None:
    root = _stage(tmp_path, ALL)
    digest = sha256_file(root / "incoming" / "equity_eod.csv")
    result = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert result.status == "success"
    archived = next((root / "raw").rglob("equity_eod*.csv"))
    assert sha256_file(archived) == digest
