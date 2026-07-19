"""End-to-end feature compute + publish orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.config import load_config_with_hash
from stock_engine.features.compute import FEATURE_COMPUTERS, compute_feature
from stock_engine.features.dag import validate_dag
from stock_engine.features.inputs import load_l1_equity_eod
from stock_engine.features.models import FeatureSetManifest
from stock_engine.features.publish import FeaturePublishRequest, publish_feature_frame
from stock_engine.features.registry import default_registry_paths, load_registry
from stock_engine.logging_utils import configure_logging


@dataclass
class FeatureRunResult:
    run_id: str
    as_of_date: date
    config_version: str
    config_hash: str
    status: str
    feature_ids: list[str] = field(default_factory=list)
    manifest: FeatureSetManifest | None = None
    errors: list[str] = field(default_factory=list)


def _merge_feature_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        msg = "no feature frames to merge"
        raise ValueError(msg)
    out = frames[0]
    for frame in frames[1:]:
        out = out.merge(frame, on=["isin", "session_date"], how="outer", validate="one_to_one")
    return out.sort_values(["isin", "session_date"]).reset_index(drop=True)


def run_feature_publish(
    *,
    data_root: Path | None = None,
    as_of_date: date,
    feature_ids: list[str] | None = None,
    feature_set: str = "core_raw",
    feature_version: str = "v1",
    config_dir: Path | None = None,
    repo_root: Path | None = None,
) -> FeatureRunResult:
    """
    Load L1 → compute registered features → validate → publish Parquet + manifest.
    """
    cfg, config_version, cfg_hash = load_config_with_hash(config_dir)
    root = data_root or Path(cfg.get("paths", {}).get("data_root", "data"))
    clean_root = root / "clean"
    features_root = root / "features"
    metadata_root = root / "metadata"

    repo = repo_root or Path(__file__).resolve().parents[3]
    registry_dir, families_path, datasets_path = default_registry_paths(repo)
    run_id = configure_logging(pipeline_stage="features")

    try:
        registry = load_registry(
            registry_dir,
            families_path,
            datasets_path=datasets_path,
        )
    except (OSError, ValueError) as exc:
        return FeatureRunResult(
            run_id=run_id,
            as_of_date=as_of_date,
            config_version=config_version,
            config_hash=cfg_hash,
            status="failed",
            errors=[f"registry: {exc}"],
        )

    if feature_ids is None:
        # Default: features that have registered computers
        feature_ids = [
            fid for fid in FEATURE_COMPUTERS if fid in {f.feature_id for f in registry.all()}
        ]
    if not feature_ids:
        return FeatureRunResult(
            run_id=run_id,
            as_of_date=as_of_date,
            config_version=config_version,
            config_hash=cfg_hash,
            status="failed",
            errors=["no feature_ids to compute"],
        )

    try:
        specs = []
        for fid in feature_ids:
            name, ver = fid.split("@", 1)
            specs.append(registry.get(name, ver))
        ordered_ids = [
            fid for fid in validate_dag(specs).topological_order() if fid in set(feature_ids)
        ]
    except (KeyError, ValueError) as exc:
        return FeatureRunResult(
            run_id=run_id,
            as_of_date=as_of_date,
            config_version=config_version,
            config_hash=cfg_hash,
            status="failed",
            feature_ids=feature_ids,
            errors=[f"dag: {exc}"],
        )

    try:
        l1 = load_l1_equity_eod(clean_root, as_of_date)
    except (OSError, ValueError) as exc:
        return FeatureRunResult(
            run_id=run_id,
            as_of_date=as_of_date,
            config_version=config_version,
            config_hash=cfg_hash,
            status="failed",
            feature_ids=ordered_ids,
            errors=[f"l1: {exc}"],
        )

    frames: list[pd.DataFrame] = []
    errors: list[str] = []
    for fid in ordered_ids:
        try:
            name, ver = fid.split("@", 1)
            spec = registry.get(name, ver)
            frames.append(compute_feature(fid, l1_equity=l1, as_of_date=as_of_date, spec=spec))
        except (KeyError, ValueError) as exc:
            errors.append(str(exc))

    if errors:
        return FeatureRunResult(
            run_id=run_id,
            as_of_date=as_of_date,
            config_version=config_version,
            config_hash=cfg_hash,
            status="failed",
            feature_ids=ordered_ids,
            errors=errors,
        )

    try:
        frame = _merge_feature_frames(frames)
        manifest = publish_feature_frame(
            FeaturePublishRequest(
                feature_set=feature_set,
                feature_version=feature_version,
                as_of_date=as_of_date,
                run_id=run_id,
                config_hash=cfg_hash,
                config_version=config_version,
                feature_ids=ordered_ids,
                frame=frame,
            ),
            registry,
            features_root=features_root,
            metadata_root=metadata_root,
        )
    except (OSError, ValueError) as exc:
        return FeatureRunResult(
            run_id=run_id,
            as_of_date=as_of_date,
            config_version=config_version,
            config_hash=cfg_hash,
            status="failed",
            feature_ids=ordered_ids,
            errors=[f"publish: {exc}"],
        )

    return FeatureRunResult(
        run_id=run_id,
        as_of_date=as_of_date,
        config_version=config_version,
        config_hash=cfg_hash,
        status="success",
        feature_ids=ordered_ids,
        manifest=manifest,
    )
