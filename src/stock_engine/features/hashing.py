"""Deterministic hashing helpers for feature frames."""

from __future__ import annotations

import hashlib
from io import BytesIO

import pandas as pd


def feature_content_hash(frame: pd.DataFrame) -> str:
    """
    SHA256 of a canonical Parquet encoding of ``frame``.

    Rows are sorted by (isin, session_date) when present; columns are sorted
    alphabetically so column order does not affect the hash.
    """
    out = frame.copy()
    sort_cols = [c for c in ("isin", "session_date") if c in out.columns]
    if sort_cols:
        out = out.sort_values(sort_cols).reset_index(drop=True)
    else:
        out = out.reset_index(drop=True)
    out = out[sorted(out.columns)]
    buf = BytesIO()
    out.to_parquet(buf, index=False)
    return hashlib.sha256(buf.getvalue()).hexdigest()
