"""Write clean Parquet datasets (L0 / L1). Deterministic column/row order."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_clean_parquet(
    df: pd.DataFrame,
    *,
    clean_root: Path,
    tier: str,
    dataset: str,
    as_of_date,
    dataset_version: str,
) -> Path:
    """
    Write to clean/{tier}/{dataset}/as_of_date=.../{dataset}__{version}.parquet
    """
    if tier not in {"l0", "l1"}:
        msg = f"tier must be l0 or l1, got {tier}"
        raise ValueError(msg)

    dest_dir = clean_root / tier / dataset / f"as_of_date={as_of_date.isoformat()}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{dataset}__{dataset_version}.parquet"

    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_object_dtype(out[col]):
            sample = out[col].dropna()
            if len(sample) and hasattr(sample.iloc[0], "isoformat"):
                out[col] = pd.to_datetime(out[col], errors="coerce")

    # Deterministic write
    out.to_parquet(dest, index=False)
    return dest
