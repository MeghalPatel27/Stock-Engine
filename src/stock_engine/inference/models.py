"""Inference manifests."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class RankSetManifest(BaseModel):
    run_id: str
    as_of_date: date
    session_date: date
    config_version: str
    config_hash: str
    rank_set: str
    rank_version: str
    horizon: int = Field(ge=1)
    model_name: str
    model_version: str
    feature_set: str
    feature_version: str
    risk_weight: float
    row_count: int = Field(ge=0)
    top_n_longs: int = Field(ge=1)
    top_n_shorts: int = Field(ge=1)
    parquet_path: str
    content_hash: str
    engine_version: str = "0.1.0"
