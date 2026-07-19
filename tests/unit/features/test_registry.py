"""Feature registry loader + metadata validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from stock_engine.features.models import FeatureSpec
from stock_engine.features.registry import load_registry

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "features"


def test_load_fixture_registry() -> None:
    registry = load_registry(
        FIXTURES / "registry",
        FIXTURES / "families.yaml",
        datasets_path=FIXTURES / "datasets.yaml",
    )
    assert len(registry) == 2
    assert "fw__base__panel@v1" in registry
    base = registry.get("fw__base__panel", "v1")
    assert base.feature_type == "raw"
    assert base.family == "other"
    assert base.computational_cost == "low"
    assert base.stability == "experimental"
    child = registry.get("fw__child__panel")
    assert child.feature_deps() == ["fw__base__panel@v1"]
    assert registry.by_family("other")
    assert registry.registry_hash()
    assert registry.datasets is not None
    assert "l1.equity_eod" in registry.datasets


def test_repo_registry_loads_raw_close_adj() -> None:
    root = Path(__file__).resolve().parents[3]
    registry = load_registry(
        root / "docs" / "features" / "registry",
        root / "docs" / "features" / "families.yaml",
        datasets_path=root / "docs" / "features" / "datasets.yaml",
    )
    assert "raw__close_adj__l1@v1" in registry
    spec = registry.get("raw__close_adj__l1", "v1")
    assert spec.feature_type == "raw"
    assert spec.dataset_deps() == ["l1.equity_eod"]
    assert registry.family_ids
    assert registry.datasets is not None
    assert len(registry.datasets) >= 1


def test_unknown_dataset_dep_fails(tmp_path: Path) -> None:
    families = tmp_path / "families.yaml"
    families.write_text("families:\n  - id: other\n    description: x\n", encoding="utf-8")
    datasets = tmp_path / "datasets.yaml"
    datasets.write_text(
        "datasets:\n  - id: l1.equity_eod\n    schema_version: v1\n"
        "    unique_key: [isin, session_date]\n",
        encoding="utf-8",
    )
    reg = tmp_path / "registry"
    reg.mkdir()
    (reg / "bad.yaml").write_text(
        """
name: fw__bad__dataset
version: v1
family: other
feature_type: raw
owner: t
description: unknown dataset
dtype: float
dependencies:
  - dataset:l1.does_not_exist
lookback_sessions: 0
pit_rule: asof_session_close
null_policy: propagate
lifecycle: experimental
validation:
  finite: true
  allow_null: true
recomputable: true
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown dataset"):
        load_registry(reg, families, datasets_path=datasets)


def test_unknown_family_fails(tmp_path: Path) -> None:
    families = tmp_path / "families.yaml"
    families.write_text("families:\n  - id: momentum\n    description: x\n", encoding="utf-8")
    datasets = tmp_path / "datasets.yaml"
    datasets.write_text(
        "datasets:\n  - id: l1.equity_eod\n    schema_version: v1\n"
        "    unique_key: [isin, session_date]\n",
        encoding="utf-8",
    )
    reg = tmp_path / "registry"
    reg.mkdir()
    (reg / "bad.yaml").write_text(
        """
name: fw__bad__family
version: v1
family: not_a_family
feature_type: raw
owner: t
description: bad family
dtype: float
dependencies:
  - dataset:l1.equity_eod
lookback_sessions: 0
pit_rule: asof_session_close
null_policy: propagate
lifecycle: experimental
validation:
  finite: true
  allow_null: true
recomputable: true
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown family"):
        load_registry(reg, families, datasets_path=datasets)


def test_feature_type_required() -> None:
    with pytest.raises(ValidationError):
        FeatureSpec.model_validate(
            {
                "name": "fw__no__type",
                "version": "v1",
                "family": "other",
                "owner": "t",
                "description": "missing feature_type",
                "dtype": "float",
                "dependencies": ["dataset:l1.equity_eod"],
                "lookback_sessions": 0,
                "null_policy": "propagate",
                "lifecycle": "experimental",
                "recomputable": True,
            }
        )


def test_dependency_prefix_enforced() -> None:
    with pytest.raises(ValidationError):
        FeatureSpec.model_validate(
            {
                "name": "fw__bad__dep",
                "version": "v1",
                "family": "other",
                "feature_type": "raw",
                "owner": "t",
                "description": "bad dep",
                "dtype": "float",
                "dependencies": ["l1.equity_eod"],
                "lookback_sessions": 0,
                "null_policy": "propagate",
                "lifecycle": "experimental",
                "recomputable": True,
            }
        )


def test_naming_convention() -> None:
    with pytest.raises(ValidationError):
        FeatureSpec.model_validate(
            {
                "name": "BadName",
                "version": "v1",
                "family": "other",
                "feature_type": "raw",
                "owner": "t",
                "description": "bad name",
                "dtype": "float",
                "dependencies": ["dataset:l1.equity_eod"],
                "lookback_sessions": 0,
                "null_policy": "propagate",
                "lifecycle": "experimental",
                "recomputable": True,
            }
        )
