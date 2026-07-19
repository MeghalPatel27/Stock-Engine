"""Feature publishing framework — writes store + metadata (no compute)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.features.models import FeatureSetManifest, FeatureSpec
from stock_engine.features.registry import FeatureRegistry
from stock_engine.features.store import FeatureStore, LocalParquetFeatureStore

KEY_COLUMNS = ("isin", "session_date")


@dataclass(frozen=True)
class FeaturePublishRequest:
    feature_set: str
    feature_version: str
    as_of_date: date
    run_id: str
    config_hash: str
    config_version: str
    feature_ids: list[str]
    frame: pd.DataFrame


def _is_ok_finite(x: object) -> bool:
    try:
        value = float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return bool(pd.notna(value) and abs(value) != float("inf"))


def validate_publish_frame(
    frame: pd.DataFrame,
    specs: list[FeatureSpec],
    *,
    production_fail_closed: bool = True,
) -> list[str]:
    """
    Validate a precomputed feature frame against registry specs.

    Returns list of error strings (empty if ok). Missing key/feature columns
    always error. Value checks fail-closed for ``production`` lifecycle when
    ``production_fail_closed`` is True.
    """
    errors: list[str] = []
    for col in KEY_COLUMNS:
        if col not in frame.columns:
            errors.append(f"missing key column {col}")

    for spec in specs:
        if spec.name not in frame.columns:
            errors.append(f"missing feature column {spec.name} for {spec.feature_id}")
            continue

        if not (production_fail_closed and spec.lifecycle == "production"):
            continue

        series = frame[spec.name]
        nums = pd.to_numeric(series, errors="coerce")

        if spec.validation.finite:
            bad = series.notna() & (~nums.map(_is_ok_finite))
            if bool(bad.any()):
                errors.append(f"{spec.feature_id}: non-finite values")

        if spec.validation.min_value is not None and bool(
            (nums.notna() & (nums < spec.validation.min_value)).any()
        ):
            errors.append(f"{spec.feature_id}: below min_value")

        if spec.validation.max_value is not None and bool(
            (nums.notna() & (nums > spec.validation.max_value)).any()
        ):
            errors.append(f"{spec.feature_id}: above max_value")

        if not spec.validation.allow_null and bool(series.isna().any()):
            errors.append(f"{spec.feature_id}: nulls not allowed")

    return errors


def _resolve_specs(registry: FeatureRegistry, feature_ids: list[str]) -> list[FeatureSpec]:
    specs: list[FeatureSpec] = []
    for fid in feature_ids:
        if "@" not in fid:
            msg = f"feature_id must be name@version, got {fid!r}"
            raise ValueError(msg)
        name, ver = fid.split("@", 1)
        specs.append(registry.get(name, ver))
    return specs


def publish_feature_frame(
    request: FeaturePublishRequest,
    registry: FeatureRegistry,
    *,
    store: FeatureStore | None = None,
    features_root: Path | None = None,
    metadata_root: Path | None = None,
) -> FeatureSetManifest:
    """
    Publish an already-computed feature frame.

    This framework does not compute features — callers supply ``request.frame``.
    """
    specs = _resolve_specs(registry, request.feature_ids)
    errors = validate_publish_frame(request.frame, specs)
    if errors:
        raise ValueError("Publish validation failed:\n- " + "\n- ".join(errors))

    if store is not None:
        store_impl: FeatureStore = store
    else:
        if features_root is None:
            msg = "features_root or store is required"
            raise ValueError(msg)
        store_impl = LocalParquetFeatureStore(features_root)

    as_of = request.as_of_date.isoformat()
    path = store_impl.write(
        request.frame,
        feature_set=request.feature_set,
        feature_version=request.feature_version,
        as_of_date=as_of,
    )

    manifest = FeatureSetManifest(
        feature_set=request.feature_set,
        feature_version=request.feature_version,
        as_of_date=as_of,
        run_id=request.run_id,
        config_hash=request.config_hash,
        config_version=request.config_version,
        registry_hash=registry.registry_hash(),
        feature_ids=list(request.feature_ids),
        row_count=len(request.frame),
        parquet_path=str(path),
    )

    if metadata_root is not None:
        dest = (
            metadata_root
            / "features"
            / "published"
            / as_of
            / f"{request.feature_set}__{request.feature_version}.json"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return manifest
