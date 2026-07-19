"""End-to-end label compute + publish (H=5 primary)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal

from stock_engine.config import load_config_with_hash
from stock_engine.features.inputs import load_l1_equity_eod, load_open_sessions
from stock_engine.labels.compute import (
    assign_labels,
    compute_forward_returns,
    validate_label_frame,
)
from stock_engine.labels.hashing import label_content_hash
from stock_engine.labels.models import LabelSetManifest
from stock_engine.labels.store import LocalParquetLabelStore
from stock_engine.logging_utils import configure_logging

UniverseMode = Literal["pilot", "l1_intersection", "phase1_filters"]
SelectionPolicy = Literal["floor", "ceil", "nearest"]


@dataclass
class LabelRunResult:
    run_id: str
    as_of_date: date
    config_version: str
    config_hash: str
    status: str
    horizon: int
    manifest: LabelSetManifest | None = None
    errors: list[str] = field(default_factory=list)


def run_label_publish(
    *,
    data_root: Path | None = None,
    as_of_date: date,
    horizon: int | None = None,
    label_set: str = "core",
    label_version: str = "v1",
    universe_mode: UniverseMode | None = None,
    selection_policy: SelectionPolicy | None = None,
    overwrite: bool = False,
    config_dir: Path | None = None,
) -> LabelRunResult:
    cfg, config_version, cfg_hash = load_config_with_hash(config_dir)
    root = data_root or Path(cfg.get("paths", {}).get("data_root", "data"))
    labels_cfg = cfg.get("labels", {})

    h = int(horizon if horizon is not None else labels_cfg.get("horizon_primary", 5))
    if h != 5:
        # ADR-06 PICK A: only H=5 in first implementation
        return LabelRunResult(
            run_id="n/a",
            as_of_date=as_of_date,
            config_version=config_version,
            config_hash=cfg_hash,
            status="failed",
            horizon=h,
            errors=[f"Only horizon=5 is supported in V1 label pipeline (got {h})"],
        )

    top_q = float(labels_cfg.get("top_quantile", 0.20))
    bot_q = float(labels_cfg.get("bottom_quantile", 0.20))
    mode: UniverseMode = universe_mode or labels_cfg.get("universe_mode", "pilot")  # type: ignore[assignment]
    policy: SelectionPolicy = selection_policy or labels_cfg.get(  # type: ignore[assignment]
        "selection_policy", "floor"
    )
    label_source = str(labels_cfg.get("label_source", "price_return_v1"))
    pilot_isins = labels_cfg.get("pilot_isins") or None
    if pilot_isins is not None:
        pilot_isins = [str(x) for x in pilot_isins]

    run_id = configure_logging(pipeline_stage="labels")
    clean_root = root / "clean"
    labels_root = root / "labels"
    metadata_root = root / "metadata"

    try:
        l1 = load_l1_equity_eod(clean_root, as_of_date)
        sessions = load_open_sessions(clean_root, as_of_date)
        forward = compute_forward_returns(l1, sessions, horizon=h, as_of_date=as_of_date)
        frame = assign_labels(
            forward,
            horizon=h,
            top_quantile=top_q,
            bottom_quantile=bot_q,
            selection_policy=policy,
            universe_mode=mode,
            label_version=label_version,
            label_source=label_source,
            pilot_isins=pilot_isins,
        )
        errors = validate_label_frame(frame, horizon=h, label_version=label_version)
        if errors:
            return LabelRunResult(
                run_id=run_id,
                as_of_date=as_of_date,
                config_version=config_version,
                config_hash=cfg_hash,
                status="failed",
                horizon=h,
                errors=errors,
            )

        store = LocalParquetLabelStore(labels_root)
        as_of = as_of_date.isoformat()
        content_hash = label_content_hash(frame)
        path = store.write(
            frame,
            label_set=label_set,
            label_version=label_version,
            horizon=h,
            as_of_date=as_of,
            overwrite=overwrite,
        )
        manifest = LabelSetManifest(
            label_set=label_set,
            label_version=label_version,
            horizon=h,
            as_of_date=as_of,
            run_id=run_id,
            config_hash=cfg_hash,
            config_version=config_version,
            label_content_hash=content_hash,
            universe_mode=mode,
            selection_policy=policy,
            top_quantile=top_q,
            bottom_quantile=bot_q,
            label_source=label_source,
            row_count=len(frame),
            parquet_path=str(path),
            extra={
                "note": (
                    "universe_mode=pilot is not suitable for production benchmarking"
                    if mode == "pilot"
                    else ""
                )
            },
        )
        dest = (
            metadata_root
            / "labels"
            / "published"
            / as_of
            / f"{label_set}__{label_version}__h{h}.json"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, NotImplementedError, FileExistsError) as exc:
        return LabelRunResult(
            run_id=run_id,
            as_of_date=as_of_date,
            config_version=config_version,
            config_hash=cfg_hash,
            status="failed",
            horizon=h,
            errors=[str(exc)],
        )

    return LabelRunResult(
        run_id=run_id,
        as_of_date=as_of_date,
        config_version=config_version,
        config_hash=cfg_hash,
        status="success",
        horizon=h,
        manifest=manifest,
    )
