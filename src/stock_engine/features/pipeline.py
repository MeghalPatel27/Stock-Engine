"""End-to-end feature compute + publish orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.config import load_config_with_hash
from stock_engine.features.compute import FEATURE_COMPUTERS, compute_feature
from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.dag import validate_dag
from stock_engine.features.inputs import load_l1_equity_eod, load_open_sessions
from stock_engine.features.models import FeatureSetManifest, FeatureSpec
from stock_engine.features.publish import FeaturePublishRequest, publish_feature_frame
from stock_engine.features.registry import FeatureRegistry, default_registry_paths, load_registry
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


def _normalize_feature_dep(dep: str, registry: FeatureRegistry) -> str:
    if "@" in dep:
        return dep
    spec = registry.get(dep)
    return spec.feature_id


def expand_feature_ids(registry: FeatureRegistry, requested: list[str]) -> list[FeatureSpec]:
    """Include transitive feature: dependencies, then return topo-sorted specs."""
    needed: set[str] = set()
    stack = list(requested)
    while stack:
        fid = stack.pop()
        if fid in needed:
            continue
        name, ver = fid.split("@", 1)
        spec = registry.get(name, ver)
        needed.add(spec.feature_id)
        for dep in spec.feature_deps():
            dep_id = _normalize_feature_dep(dep, registry)
            if dep_id not in needed:
                stack.append(dep_id)

    specs = [registry.get(*fid.split("@", 1)) for fid in needed]
    order = validate_dag(specs).topological_order()
    return [registry.get(*fid.split("@", 1)) for fid in order]


def run_feature_publish(
    *,
    data_root: Path | None = None,
    as_of_date: date,
    feature_ids: list[str] | None = None,
    feature_set: str = "core",
    feature_version: str = "v1",
    config_dir: Path | None = None,
    repo_root: Path | None = None,
) -> FeatureRunResult:
    """
    Load L1 → compute registered features (DAG order) → validate → publish.
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
        ordered_specs = expand_feature_ids(registry, feature_ids)
        ordered_ids = [s.feature_id for s in ordered_specs]
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

    missing_computers = [fid for fid in ordered_ids if fid not in FEATURE_COMPUTERS]
    if missing_computers:
        return FeatureRunResult(
            run_id=run_id,
            as_of_date=as_of_date,
            config_version=config_version,
            config_hash=cfg_hash,
            status="failed",
            feature_ids=ordered_ids,
            errors=[f"no computer for {fid}" for fid in missing_computers],
        )

    try:
        l1 = load_l1_equity_eod(clean_root, as_of_date)
        sessions = load_open_sessions(clean_root, as_of_date)
    except (OSError, ValueError) as exc:
        return FeatureRunResult(
            run_id=run_id,
            as_of_date=as_of_date,
            config_version=config_version,
            config_hash=cfg_hash,
            status="failed",
            feature_ids=ordered_ids,
            errors=[f"inputs: {exc}"],
        )

    ctx = ComputeContext(
        as_of_date=as_of_date,
        l1_equity=l1,
        open_sessions=sessions,
    )
    frames: list[pd.DataFrame] = []
    errors: list[str] = []
    for spec in ordered_specs:
        try:
            frame = compute_feature(spec.feature_id, ctx=ctx, spec=spec)
            ctx.features[spec.feature_id] = frame
            frames.append(frame)
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
