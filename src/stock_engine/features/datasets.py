"""Dataset registry for feature dependency validation."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class DatasetSpec(BaseModel):
    """Known dataset that features may depend on via dataset:<id>."""

    id: str = Field(min_length=1)
    schema_version: str = Field(min_length=1, pattern=r"^v[0-9]+$")
    description: str = ""
    unique_key: list[str] = Field(min_length=1)
    required_columns: list[str] = Field(default_factory=list)


class DatasetsFile(BaseModel):
    datasets: list[DatasetSpec]


class DatasetRegistry:
    def __init__(self, datasets: dict[str, DatasetSpec], *, root: Path) -> None:
        self._datasets = datasets
        self.root = root

    def __contains__(self, dataset_id: object) -> bool:
        return isinstance(dataset_id, str) and dataset_id in self._datasets

    def __len__(self) -> int:
        return len(self._datasets)

    def get(self, dataset_id: str) -> DatasetSpec:
        if dataset_id not in self._datasets:
            msg = f"Unknown dataset {dataset_id}"
            raise KeyError(msg)
        return self._datasets[dataset_id]

    def all(self) -> list[DatasetSpec]:
        return sorted(self._datasets.values(), key=lambda d: d.id)

    def ids(self) -> set[str]:
        return set(self._datasets)


def load_dataset_registry(path: Path) -> DatasetRegistry:
    if not path.exists():
        msg = f"Missing datasets file: {path}"
        raise FileNotFoundError(msg)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    parsed = DatasetsFile.model_validate(raw)
    datasets: dict[str, DatasetSpec] = {}
    for spec in parsed.datasets:
        if spec.id in datasets:
            msg = f"Duplicate dataset id: {spec.id}"
            raise ValueError(msg)
        datasets[spec.id] = spec
    if not datasets:
        msg = "datasets.yaml must declare at least one dataset"
        raise ValueError(msg)
    return DatasetRegistry(datasets, root=path)


def validate_dataset_deps(
    feature_dataset_deps: list[tuple[str, str]],
    dataset_registry: DatasetRegistry,
) -> list[str]:
    """
    Validate dataset:<id> refs.

    ``feature_dataset_deps`` is a list of (feature_id, dataset_id).
    """
    errors: list[str] = []
    known = dataset_registry.ids()
    for feature_id, dataset_id in feature_dataset_deps:
        if dataset_id not in known:
            errors.append(f"{feature_id}: unknown dataset dependency dataset:{dataset_id}")
    return errors


def default_datasets_path(repo_root: Path) -> Path:
    return repo_root / "docs" / "features" / "datasets.yaml"
