"""Published dataset metadata sidecars for versioned clean outputs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class PublishedDatasetMeta:
    """Metadata for a published clean dataset (L0/L1)."""

    dataset: str
    schema_version: str
    dataset_version: str
    adjustment_method: str | None
    config_hash: str
    config_version: str
    run_id: str
    as_of_date: str
    tier: str
    row_count: int
    parquet_path: str


def write_published_dataset_meta(meta: PublishedDatasetMeta, metadata_root: Path) -> Path:
    dest_dir = metadata_root / "published" / meta.as_of_date
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{meta.tier}__{meta.dataset}__{meta.dataset_version}.json"
    path.write_text(json.dumps(asdict(meta), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def published_meta_for_l1_equity(
    *,
    schema_version: str,
    dataset_version: str,
    adjustment_method: str,
    config_hash: str,
    config_version: str,
    run_id: str,
    as_of_date: date,
    row_count: int,
    parquet_path: str,
) -> PublishedDatasetMeta:
    return PublishedDatasetMeta(
        dataset="equity_eod_l1",
        schema_version=schema_version,
        dataset_version=dataset_version,
        adjustment_method=adjustment_method,
        config_hash=config_hash,
        config_version=config_version,
        run_id=run_id,
        as_of_date=as_of_date.isoformat(),
        tier="l1",
        row_count=row_count,
        parquet_path=parquet_path,
    )
