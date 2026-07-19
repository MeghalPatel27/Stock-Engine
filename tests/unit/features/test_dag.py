"""Feature DAG validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from stock_engine.features.dag import validate_dag
from stock_engine.features.registry import load_registry

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "features"


def test_topological_order_parent_before_child() -> None:
    registry = load_registry(FIXTURES / "registry", FIXTURES / "families.yaml")
    dag = validate_dag(registry.all())
    order = dag.topological_order()
    assert order.index("fw__base__panel@v1") < order.index("fw__child__panel@v1")


def test_cycle_rejected() -> None:
    with pytest.raises(ValueError, match="cycle"):
        load_registry(
            FIXTURES / "bad_cycle" / "registry",
            FIXTURES / "bad_cycle" / "families.yaml",
        )
