"""Pydantic models for feature registry metadata."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

FeatureType = Literal["raw", "rolling", "cross_sectional", "derived", "composite"]
Lifecycle = Literal["experimental", "candidate", "production", "deprecated"]
NullPolicy = Literal["propagate", "skip_row", "fail_run"]
ComputationalCost = Literal["low", "medium", "high"]
Stability = Literal["experimental", "stable"]
PitRule = Literal["asof_session_close"]


class FeatureValidation(BaseModel):
    finite: bool = True
    min_value: float | None = None
    max_value: float | None = None
    allow_null: bool = True


class FeatureSpec(BaseModel):
    """Machine-readable feature definition (registry entry)."""

    name: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9]*(__[a-z0-9]+)+$")
    version: str = Field(min_length=1, pattern=r"^v[0-9]+$")
    family: str = Field(min_length=1)
    feature_type: FeatureType
    owner: str = Field(min_length=1)
    description: str = Field(min_length=1)
    dtype: Literal["float", "int", "bool", "category"]
    unit: str | None = None
    dependencies: list[str] = Field(min_length=1)
    lookback_sessions: int = Field(ge=0)
    pit_rule: PitRule = "asof_session_close"
    null_policy: NullPolicy
    lifecycle: Lifecycle
    validation: FeatureValidation = Field(default_factory=FeatureValidation)
    recomputable: bool = True
    computational_cost: ComputationalCost | None = None
    stability: Stability | None = None

    @field_validator("dependencies")
    @classmethod
    def _deps_format(cls, deps: list[str]) -> list[str]:
        for d in deps:
            if not (d.startswith("dataset:") or d.startswith("feature:")):
                msg = f"Dependency must start with dataset: or feature: — got {d!r}"
                raise ValueError(msg)
        return deps

    @property
    def feature_id(self) -> str:
        return f"{self.name}@{self.version}"

    def feature_deps(self) -> list[str]:
        return [d.removeprefix("feature:") for d in self.dependencies if d.startswith("feature:")]

    def dataset_deps(self) -> list[str]:
        return [d.removeprefix("dataset:") for d in self.dependencies if d.startswith("dataset:")]


class FeatureFamily(BaseModel):
    id: str
    description: str = ""


class FamiliesFile(BaseModel):
    families: list[FeatureFamily]

    def ids(self) -> set[str]:
        return {f.id for f in self.families}


class FeatureSetManifest(BaseModel):
    """Metadata for a published feature-set Parquet."""

    feature_set: str
    feature_version: str
    as_of_date: str
    run_id: str
    config_hash: str
    config_version: str
    registry_hash: str
    feature_ids: list[str]
    row_count: int
    parquet_path: str
    extra: dict[str, Any] = Field(default_factory=dict)
