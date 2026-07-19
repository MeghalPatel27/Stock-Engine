"""Attach lineage columns for clean publishes."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from stock_engine.ingest.datasets import LINEAGE_COLUMNS


def attach_lineage(
    df: pd.DataFrame,
    *,
    source_file: str,
    raw_sha256: str,
    ingested_at: datetime,
    provider: str,
    schema_version: str,
    dataset_version: str,
    run_id: str,
) -> pd.DataFrame:
    out = df.copy()
    out["source_file"] = source_file
    out["raw_sha256"] = raw_sha256
    out["ingested_at"] = pd.Timestamp(ingested_at)
    out["provider"] = provider
    out["schema_version"] = schema_version
    out["dataset_version"] = dataset_version
    out["run_id"] = run_id
    # Keep business cols then lineage in stable order
    business = [c for c in out.columns if c not in LINEAGE_COLUMNS]
    return out[business + list(LINEAGE_COLUMNS)]
