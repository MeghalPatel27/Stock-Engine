"""Tests for mom__ret__1d."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.compute.mom_ret import compute_mom_ret_1d
from stock_engine.features.compute.raw_close_adj import compute_raw_close_adj_l1
from stock_engine.features.pipeline import expand_feature_ids, run_feature_publish
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


def _registry():
    return load_registry(
        REPO / "docs" / "features" / "registry",
        REPO / "docs" / "features" / "families.yaml",
        datasets_path=REPO / "docs" / "features" / "datasets.yaml",
    )


def test_mom_ret_1d_formula_and_first_null() -> None:
    registry = _registry()
    raw_spec = registry.get("raw__close_adj__l1", "v1")
    mom_spec = registry.get("mom__ret__1d", "v1")

    sessions = pd.DatetimeIndex(pd.to_datetime(["2026-07-14", "2026-07-15", "2026-07-16"]))
    l1 = pd.DataFrame(
        {
            "isin": ["INE001", "INE001", "INE001"],
            "session_date": sessions,
            "close_adj": [100.0, 110.0, 99.0],
        }
    )
    ctx = ComputeContext(as_of_date=date(2026, 7, 16), l1_equity=l1, open_sessions=sessions)
    raw = compute_raw_close_adj_l1(ctx, raw_spec)
    ctx.features[raw_spec.feature_id] = raw
    mom = compute_mom_ret_1d(ctx, mom_spec)

    assert mom["mom__ret__1d"].isna().iloc[0]
    assert abs(float(mom["mom__ret__1d"].iloc[1]) - 0.10) < 1e-12
    assert abs(float(mom["mom__ret__1d"].iloc[2]) - (99 / 110 - 1)) < 1e-12


def test_expand_includes_upstream_raw() -> None:
    registry = _registry()
    specs = expand_feature_ids(registry, ["mom__ret__1d@v1"])
    ids = [s.feature_id for s in specs]
    assert ids.index("raw__close_adj__l1@v1") < ids.index("mom__ret__1d@v1")


def test_e2e_publish_mom_with_dependency(tmp_path: Path) -> None:
    root = tmp_path / "data"
    incoming = root / "incoming"
    incoming.mkdir(parents=True)
    for name in ALL:
        shutil.copy(FIXTURES_INCOMING / name, incoming / name)
    for sub in ("raw", "clean", "metadata", "features"):
        (root / sub).mkdir()

    ingest = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert ingest.status == "success", ingest.errors
    l1_dirs = list((root / "clean" / "l1" / "equity_eod").glob("as_of_date=*"))
    published_as_of = date.fromisoformat(l1_dirs[0].name.split("=", 1)[1])

    result = run_feature_publish(
        data_root=root,
        as_of_date=published_as_of,
        feature_ids=["mom__ret__1d@v1"],
        feature_set="core",
        feature_version="v1",
        repo_root=REPO,
    )
    assert result.status == "success", result.errors
    assert result.feature_ids == ["raw__close_adj__l1@v1", "mom__ret__1d@v1"]

    got = LocalParquetFeatureStore(root / "features").read(
        feature_set="core",
        feature_version="v1",
        as_of_date=published_as_of.isoformat(),
    )
    assert "mom__ret__1d" in got.columns
    assert "raw__close_adj__l1" in got.columns
    # At least one non-null return after lookback
    assert got["mom__ret__1d"].notna().any()
