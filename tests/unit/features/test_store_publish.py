"""Feature store + publisher framework tests (no feature compute)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from stock_engine.features.publish import FeaturePublishRequest, publish_feature_frame
from stock_engine.features.registry import load_registry
from stock_engine.features.store import LocalParquetFeatureStore

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "features"


def test_local_parquet_roundtrip(tmp_path: Path) -> None:
    store = LocalParquetFeatureStore(tmp_path / "features")
    frame = pd.DataFrame(
        {
            "isin": ["INE001", "INE002"],
            "session_date": ["2026-07-17", "2026-07-17"],
            "fw__base__panel": [1.0, 2.0],
        }
    )
    path = store.write(
        frame,
        feature_set="fixture_set",
        feature_version="v1",
        as_of_date="2026-07-17",
    )
    assert path.exists()
    assert store.exists(feature_set="fixture_set", feature_version="v1", as_of_date="2026-07-17")
    got = store.read(feature_set="fixture_set", feature_version="v1", as_of_date="2026-07-17")
    assert list(got["isin"]) == ["INE001", "INE002"]


def test_publish_writes_manifest(tmp_path: Path) -> None:
    registry = load_registry(FIXTURES / "registry", FIXTURES / "families.yaml")
    frame = pd.DataFrame(
        {
            "isin": ["INE001"],
            "session_date": ["2026-07-17"],
            "fw__base__panel": [0.5],
            "fw__child__panel": [0.25],
        }
    )
    request = FeaturePublishRequest(
        feature_set="fixture_set",
        feature_version="v1",
        as_of_date=date(2026, 7, 17),
        run_id="run-test",
        config_hash="abc",
        config_version="cfg-v1",
        feature_ids=["fw__base__panel@v1", "fw__child__panel@v1"],
        frame=frame,
    )
    manifest = publish_feature_frame(
        request,
        registry,
        features_root=tmp_path / "features",
        metadata_root=tmp_path / "metadata",
    )
    assert manifest.row_count == 1
    assert manifest.registry_hash == registry.registry_hash()
    meta = tmp_path / "metadata" / "features" / "published" / "2026-07-17" / "fixture_set__v1.json"
    assert meta.exists()


def test_production_fail_closed_rejects_nulls(tmp_path: Path) -> None:
    registry = load_registry(
        FIXTURES / "prod" / "registry",
        FIXTURES / "prod" / "families.yaml",
    )
    frame = pd.DataFrame(
        {
            "isin": ["INE001"],
            "session_date": ["2026-07-17"],
            "fw__prod__panel": [None],
        }
    )
    request = FeaturePublishRequest(
        feature_set="prod_set",
        feature_version="v1",
        as_of_date=date(2026, 7, 17),
        run_id="run-test",
        config_hash="abc",
        config_version="cfg-v1",
        feature_ids=["fw__prod__panel@v1"],
        frame=frame,
    )
    with pytest.raises(ValueError, match="nulls not allowed"):
        publish_feature_frame(request, registry, features_root=tmp_path / "features")


def test_production_fail_closed_rejects_out_of_range(tmp_path: Path) -> None:
    registry = load_registry(
        FIXTURES / "prod" / "registry",
        FIXTURES / "prod" / "families.yaml",
    )
    frame = pd.DataFrame(
        {
            "isin": ["INE001"],
            "session_date": ["2026-07-17"],
            "fw__prod__panel": [1.5],
        }
    )
    request = FeaturePublishRequest(
        feature_set="prod_set",
        feature_version="v1",
        as_of_date=date(2026, 7, 17),
        run_id="run-test",
        config_hash="abc",
        config_version="cfg-v1",
        feature_ids=["fw__prod__panel@v1"],
        frame=frame,
    )
    with pytest.raises(ValueError, match="above max_value"):
        publish_feature_frame(request, registry, features_root=tmp_path / "features")
