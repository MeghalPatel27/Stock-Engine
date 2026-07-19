"""Feature registry lint CLI tests."""

from __future__ import annotations

from pathlib import Path

from stock_engine.features.cli import main
from stock_engine.features.lint import lint_feature_registry


def test_lint_repo_registry_ok() -> None:
    root = Path(__file__).resolve().parents[3]
    assert lint_feature_registry(root) == []


def test_lint_cli_ok() -> None:
    root = Path(__file__).resolve().parents[3]
    assert main(["--repo-root", str(root)]) == 0
