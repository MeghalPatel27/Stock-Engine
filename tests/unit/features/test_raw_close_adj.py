"""Tests for raw__close_adj__l1 compute + publish path."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.features.compute.raw_close_adj import compute_raw_close_adj_l1
from stock_engine.features.pipeline import run_feature_publish
from stock_engine.features.registry import load_registry
from stock_engine.features.store import LocalParquetFeatureStore
from stock_engine.ingest.pipeline import run_ingest

FIXTURES_INCOMING = Path(__file__).resolve().parents[2] / "fixtures" / "incoming"
REPO = Path(__file__).resolve().parents[3]

ALL = [
    "equity_eod.csv",
    "corporate_actions.csv",
    "symbol_isin_map.csv",
    "trading_calendar.csv",
]


def _stage_ingest(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    incoming = root / "incoming"
    incoming.mkdir(parents=True)
    for name in ALL:
        shutil.copy(FIXTURES_INCOMING / name, incoming / name)
    for sub in ("raw", "clean", "metadata", "features"):
        (root / sub).mkdir()
    return root


def test_compute_matches_l1_close_adj() -> None:
    registry = load_registry(
        REPO / "docs" / "features" / "registry",
        REPO / "docs" / "features" / "families.yaml",
        datasets_path=REPO / "docs" / "features" / "datasets.yaml",
    )
    spec = registry.get("raw__close_adj__l1", "v1")
    l1 = pd.DataFrame(
        {
            "isin": ["INE001", "INE001", "INE002"],
            "session_date": ["2026-07-15", "2026-07-16", "2026-07-16"],
            "close_adj": [100.0, 101.0, 50.0],
            "close_raw": [100.0, 101.0, 50.0],
        }
    )
    out = compute_raw_close_adj_l1(l1, as_of_date=date(2026, 7, 16), spec=spec)
    assert list(out.columns) == ["isin", "session_date", "raw__close_adj__l1"]
    assert len(out) == 3
    assert out["raw__close_adj__l1"].tolist() == [100.0, 101.0, 50.0]


def test_compute_pit_excludes_future_sessions() -> None:
    registry = load_registry(
        REPO / "docs" / "features" / "registry",
        REPO / "docs" / "features" / "families.yaml",
        datasets_path=REPO / "docs" / "features" / "datasets.yaml",
    )
    spec = registry.get("raw__close_adj__l1", "v1")
    l1 = pd.DataFrame(
        {
            "isin": ["INE001", "INE001"],
            "session_date": ["2026-07-15", "2026-07-17"],
            "close_adj": [100.0, 110.0],
        }
    )
    out = compute_raw_close_adj_l1(l1, as_of_date=date(2026, 7, 15), spec=spec)
    assert len(out) == 1
    assert float(out["raw__close_adj__l1"].iloc[0]) == 100.0


def test_e2e_ingest_then_publish_feature(tmp_path: Path) -> None:
    root = _stage_ingest(tmp_path)
    ingest = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert ingest.status == "success", ingest.errors

    l1_dirs = list((root / "clean" / "l1" / "equity_eod").glob("as_of_date=*"))
    assert l1_dirs
    published_as_of = date.fromisoformat(l1_dirs[0].name.split("=", 1)[1])

    result = run_feature_publish(
        data_root=root,
        as_of_date=published_as_of,
        feature_ids=["raw__close_adj__l1@v1"],
        feature_set="core_raw",
        feature_version="v1",
        repo_root=REPO,
    )
    assert result.status == "success", result.errors
    assert result.manifest is not None
    assert result.manifest.row_count > 0
    assert result.manifest.feature_content_hash

    store = LocalParquetFeatureStore(root / "features")
    got = store.read(
        feature_set="core_raw",
        feature_version="v1",
        as_of_date=published_as_of.isoformat(),
    )
    assert "raw__close_adj__l1" in got.columns
    l1 = pd.read_parquet(next((root / "clean" / "l1" / "equity_eod").rglob("*.parquet")))
    merged = got.merge(
        l1[["isin", "session_date", "close_adj"]],
        on=["isin", "session_date"],
        how="left",
    )
    assert (merged["raw__close_adj__l1"] == merged["close_adj"]).all()

    meta = (
        root
        / "metadata"
        / "features"
        / "published"
        / published_as_of.isoformat()
        / "core_raw__v1.json"
    )
    assert meta.exists()
