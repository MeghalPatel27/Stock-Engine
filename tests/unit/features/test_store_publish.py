"""Feature store + publisher framework tests (no feature compute)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from stock_engine.features.hashing import feature_content_hash
from stock_engine.features.publish import FeaturePublishRequest, publish_feature_frame
from stock_engine.features.registry import load_registry
from stock_engine.features.store import LocalParquetFeatureStore

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "features"


def _registry():
    return load_registry(
        FIXTURES / "registry",
        FIXTURES / "families.yaml",
        datasets_path=FIXTURES / "datasets.yaml",
    )


def _prod_registry():
    return load_registry(
        FIXTURES / "prod" / "registry",
        FIXTURES / "prod" / "families.yaml",
        datasets_path=FIXTURES / "datasets.yaml",
    )


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


def test_publish_writes_manifest_and_content_hash(tmp_path: Path) -> None:
    registry = _registry()
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
    assert manifest.feature_content_hash == feature_content_hash(frame)
    meta = tmp_path / "metadata" / "features" / "published" / "2026-07-17" / "fixture_set__v1.json"
    assert meta.exists()


def test_publish_rejects_duplicate_keys(tmp_path: Path) -> None:
    registry = _registry()
    frame = pd.DataFrame(
        {
            "isin": ["INE001", "INE001"],
            "session_date": ["2026-07-17", "2026-07-17"],
            "fw__base__panel": [0.5, 0.6],
            "fw__child__panel": [0.25, 0.26],
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
    with pytest.raises(ValueError, match="duplicate keys"):
        publish_feature_frame(request, registry, features_root=tmp_path / "features")


def test_production_fail_closed_rejects_nulls(tmp_path: Path) -> None:
    registry = _prod_registry()
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
    registry = _prod_registry()
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


def test_content_hash_stable_under_column_reorder() -> None:
    a = pd.DataFrame(
        {
            "fw__base__panel": [1.0],
            "isin": ["INE001"],
            "session_date": ["2026-07-17"],
        }
    )
    b = pd.DataFrame(
        {
            "isin": ["INE001"],
            "session_date": ["2026-07-17"],
            "fw__base__panel": [1.0],
        }
    )
    assert feature_content_hash(a) == feature_content_hash(b)
