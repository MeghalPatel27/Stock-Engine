"""Write clean Parquet datasets (production format)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_clean_parquet(
    df: pd.DataFrame,
    *,
    clean_root: Path,
    dataset: str,
    as_of_date,
    dataset_version: str,
) -> Path:
    """Write partitioned clean dataset; overwrites same as_of+version publish path."""
    dest_dir = clean_root / dataset / f"as_of_date={as_of_date.isoformat()}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{dataset}__{dataset_version}.parquet"
    # Convert date objects to datetime64 for parquet friendliness
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            sample = out[col].dropna()
            if len(sample) and hasattr(sample.iloc[0], "isoformat"):
                out[col] = pd.to_datetime(out[col], errors="coerce")
    out.to_parquet(dest, index=False)
    return dest
