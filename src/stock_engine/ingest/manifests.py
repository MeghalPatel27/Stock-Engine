"""Manifest / DQ report persistence under data/metadata/."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from stock_engine.contracts import RunMetadata
from stock_engine.ingest.raw_store import RawSidecar
from stock_engine.ingest.validate import DQReport


@dataclass
class DatasetManifest:
    dataset: str
    dataset_version: str
    as_of_date: str
    provider: str
    raw_path: str
    clean_path: str | None
    sha256: str
    row_count: int
    dq_ok: bool
    dq_issues: list[dict[str, str]] = field(default_factory=list)


def write_run_metadata(meta: RunMetadata, metadata_root: Path) -> Path:
    runs = metadata_root / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    path = runs / f"{meta.run_id}.json"
    path.write_text(meta.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def write_dataset_manifest(manifest: DatasetManifest, metadata_root: Path) -> Path:
    dest_dir = metadata_root / "manifests" / manifest.as_of_date
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{manifest.dataset}__{manifest.dataset_version}.json"
    path.write_text(json.dumps(asdict(manifest), indent=2) + "\n", encoding="utf-8")
    return path


def write_pipeline_state(
    metadata_root: Path,
    *,
    run_id: str,
    as_of_date: date,
    status: str,
    detail: dict[str, Any],
) -> Path:
    dest_dir = metadata_root / "pipeline"
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{run_id}.json"
    payload = {
        "run_id": run_id,
        "as_of_date": as_of_date.isoformat(),
        "status": status,
        "detail": detail,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def dq_to_dicts(report: DQReport) -> list[dict[str, str]]:
    return [{"code": i.code, "message": i.message} for i in report.issues]


def sidecar_to_dict(sidecar: RawSidecar) -> dict[str, Any]:
    return asdict(sidecar)
