"""Feature registry lint checks for CI / local use."""

from __future__ import annotations

from pathlib import Path

from stock_engine.features.registry import default_registry_paths, load_registry


def lint_feature_registry(repo_root: Path) -> list[str]:
    """
    Run registry lint checks. Returns a list of error strings (empty if ok).
    """
    registry_dir, families_path, datasets_path = default_registry_paths(repo_root)
    try:
        load_registry(
            registry_dir,
            families_path,
            datasets_path=datasets_path,
            validate_graph=True,
            validate_datasets=True,
        )
    except (OSError, ValueError) as exc:
        return [str(exc)]
    return []
