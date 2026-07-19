"""Label publish metadata models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

UniverseMode = Literal["pilot", "l1_intersection", "phase1_filters"]
SelectionPolicy = Literal["floor", "ceil", "nearest"]
LabelClass = Literal["bullish", "bearish", "neutral"]


class LabelSetManifest(BaseModel):
    label_set: str
    label_version: str
    horizon: int
    as_of_date: str
    run_id: str
    config_hash: str
    config_version: str
    label_content_hash: str
    universe_mode: UniverseMode
    selection_policy: SelectionPolicy
    top_quantile: float
    bottom_quantile: float
    label_source: str
    row_count: int
    parquet_path: str
    extra: dict[str, Any] = Field(default_factory=dict)
