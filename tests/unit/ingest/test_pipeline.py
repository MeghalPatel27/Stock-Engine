"""Ingest pipeline tests — local CSV only, no network."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.ingest.local_csv import LocalIncomingCsvSource
from stock_engine.ingest.pipeline import run_ingest
from stock_engine.ingest.raw_store import sha256_file

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "incoming"


def _stage_incoming(tmp_path: Path, names: list[str]) -> Path:
    root = tmp_path / "data"
    incoming = root / "incoming"
    incoming.mkdir(parents=True)
    for name in names:
        shutil.copy(FIXTURES / name, incoming / name)
    (root / "raw").mkdir()
    (root / "clean").mkdir()
    (root / "metadata").mkdir()
    return root


def test_local_source_lists_datasets(tmp_path: Path) -> None:
    root = _stage_incoming(
        tmp_path,
        ["equity_eod.csv", "corporate_actions.csv", "symbol_isin_map.csv"],
    )
    src = LocalIncomingCsvSource(root / "incoming")
    arts = src.list_artifacts()
    assert {a.dataset for a in arts} == {
        "equity_eod",
        "corporate_actions",
        "symbol_isin_map",
    }


def test_ingest_success_writes_parquet_and_metadata(tmp_path: Path) -> None:
    root = _stage_incoming(
        tmp_path,
        ["equity_eod.csv", "corporate_actions.csv", "symbol_isin_map.csv"],
    )
    result = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert result.status == "success"
    assert result.errors == []
    assert len(result.config_hash) == 64

    clean_eq = list((root / "clean" / "equity_eod").rglob("*.parquet"))
    clean_ca = list((root / "clean" / "corporate_actions").rglob("*.parquet"))
    assert len(clean_eq) == 1
    assert len(clean_ca) == 1
    df = pd.read_parquet(clean_eq[0])
    assert "isin" in df.columns
    assert df["isin"].iloc[0].startswith("INE")

    raw_files = list((root / "raw").rglob("*.csv"))
    assert raw_files
    sidecar = list((root / "raw").rglob("*.sha256.json"))
    assert sidecar
    assert (root / "metadata" / "runs" / f"{result.run_id}.json").exists()


def test_ingest_fails_without_corporate_actions(tmp_path: Path) -> None:
    root = _stage_incoming(tmp_path, ["equity_eod.csv"])
    result = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert result.status == "failed"
    assert any("corporate_actions" in e for e in result.errors)
    # fail closed — no clean publish
    assert list((root / "clean").rglob("*.parquet")) == []


def test_ingest_fails_on_missing_close(tmp_path: Path) -> None:
    root = _stage_incoming(tmp_path, ["equity_eod.csv", "corporate_actions.csv"])
    bad = root / "incoming" / "equity_eod.csv"
    bad.write_text(
        "isin,symbol,session_date,close\nINE002A01018,RELIANCE,2026-07-18,\n",
        encoding="utf-8",
    )
    result = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert result.status == "failed"
    assert list((root / "clean" / "equity_eod").rglob("*.parquet")) == []


def test_raw_checksum_stable(tmp_path: Path) -> None:
    root = _stage_incoming(tmp_path, ["equity_eod.csv", "corporate_actions.csv"])
    src_file = root / "incoming" / "equity_eod.csv"
    digest = sha256_file(src_file)
    result = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert result.status == "success"
    archived = next((root / "raw").rglob("equity_eod*.csv"))
    assert sha256_file(archived) == digest
