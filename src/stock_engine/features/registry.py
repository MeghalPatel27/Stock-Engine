"""Load and validate the feature registry from YAML."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from stock_engine.features.dag import validate_dag
from stock_engine.features.datasets import (
    DatasetRegistry,
    load_dataset_registry,
    validate_dataset_deps,
)
from stock_engine.features.models import FamiliesFile, FeatureSpec


class FeatureRegistry:
    def __init__(
        self,
        features: dict[str, FeatureSpec],
        family_ids: set[str],
        *,
        root: Path,
        datasets: DatasetRegistry | None = None,
    ) -> None:
        self._features = features
        self.family_ids = family_ids
        self.root = root
        self.datasets = datasets

    def __contains__(self, feature_id: object) -> bool:
        return isinstance(feature_id, str) and feature_id in self._features

    def __len__(self) -> int:
        return len(self._features)

    def get(self, name: str, version: str | None = None) -> FeatureSpec:
        if version:
            key = f"{name}@{version}"
            if key not in self._features:
                msg = f"Unknown feature {key}"
                raise KeyError(msg)
            return self._features[key]
        matches = [f for f in self._features.values() if f.name == name]
        if not matches:
            msg = f"Unknown feature {name}"
            raise KeyError(msg)
        if len(matches) > 1:
            msg = f"Multiple versions for {name}; pass version explicitly"
            raise KeyError(msg)
        return matches[0]

    def all(self) -> list[FeatureSpec]:
        return sorted(self._features.values(), key=lambda f: f.feature_id)

    def active(self) -> list[FeatureSpec]:
        """Non-deprecated features (candidates for compute jobs)."""
        return [f for f in self.all() if f.lifecycle != "deprecated"]

    def by_family(self, family: str) -> list[FeatureSpec]:
        return [f for f in self.all() if f.family == family]

    def by_lifecycle(self, lifecycle: str) -> list[FeatureSpec]:
        return [f for f in self.all() if f.lifecycle == lifecycle]

    def by_feature_type(self, feature_type: str) -> list[FeatureSpec]:
        return [f for f in self.all() if f.feature_type == feature_type]

    def registry_hash(self) -> str:
        payload = [
            f.model_dump(mode="json")
            for f in sorted(self._features.values(), key=lambda x: x.feature_id)
        ]
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_registry(
    registry_dir: Path,
    families_path: Path,
    *,
    datasets_path: Path | None = None,
    validate_graph: bool = True,
    validate_datasets: bool = True,
) -> FeatureRegistry:
    """
    Load family catalog + all feature YAML files.

    Raises ValueError on schema/family/DAG/dataset errors.
    """
    if not families_path.exists():
        msg = f"Missing families file: {families_path}"
        raise FileNotFoundError(msg)

    families_raw = yaml.safe_load(families_path.read_text(encoding="utf-8")) or {}
    families = FamiliesFile.model_validate(families_raw)
    family_ids = families.ids()
    if not family_ids:
        msg = "families.yaml must declare at least one family"
        raise ValueError(msg)

    dataset_registry: DatasetRegistry | None = None
    if validate_datasets:
        if datasets_path is None:
            msg = "datasets_path is required when validate_datasets=True"
            raise ValueError(msg)
        dataset_registry = load_dataset_registry(datasets_path)

    features: dict[str, FeatureSpec] = {}
    errors: list[str] = []

    if registry_dir.exists():
        paths = sorted(registry_dir.glob("*.yaml")) + sorted(registry_dir.glob("*.yml"))
    else:
        paths = []

    skip_names = {"families.yaml", "families.yml", "datasets.yaml", "datasets.yml"}
    for path in paths:
        if path.name.startswith("_"):
            continue
        if path.name in skip_names:
            continue
        if path.resolve() == families_path.resolve():
            continue
        if datasets_path is not None and path.resolve() == datasets_path.resolve():
            continue
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            spec = FeatureSpec.model_validate(raw)
        except (yaml.YAMLError, ValidationError, OSError) as exc:
            errors.append(f"{path.name}: {exc}")
            continue

        if spec.family not in family_ids:
            errors.append(f"{path.name}: unknown family {spec.family!r}")
            continue

        if spec.feature_id in features:
            errors.append(f"{path.name}: duplicate feature_id {spec.feature_id}")
            continue

        features[spec.feature_id] = spec

    if errors:
        raise ValueError("Registry validation failed:\n- " + "\n- ".join(errors))

    if dataset_registry is not None:
        dep_pairs = [
            (spec.feature_id, dep) for spec in features.values() for dep in spec.dataset_deps()
        ]
        ds_errors = validate_dataset_deps(dep_pairs, dataset_registry)
        if ds_errors:
            raise ValueError("Registry validation failed:\n- " + "\n- ".join(ds_errors))

    registry = FeatureRegistry(
        features,
        family_ids,
        root=registry_dir,
        datasets=dataset_registry,
    )
    if validate_graph:
        validate_dag(registry.all())
    return registry


def default_registry_paths(repo_root: Path) -> tuple[Path, Path, Path]:
    """Return (registry_dir, families_path, datasets_path)."""
    return (
        repo_root / "docs" / "features" / "registry",
        repo_root / "docs" / "features" / "families.yaml",
        repo_root / "docs" / "features" / "datasets.yaml",
    )
