#!/usr/bin/env python3
"""Remove local caches and (optionally) generated data artifacts."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _rm_tree_contents(path: Path, *, keep_gitkeep: bool = True) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        if keep_gitkeep and child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean local caches / data artifacts")
    parser.add_argument(
        "--data",
        action="store_true",
        help="Also clear data/raw, clean, features, metadata (keeps .gitkeep)",
    )
    args = parser.parse_args()

    for name in (".pytest_cache", ".ruff_cache", ".mypy_cache"):
        p = ROOT / name
        if p.exists():
            shutil.rmtree(p)

    if args.data:
        for name in ("raw", "clean", "features", "metadata"):
            _rm_tree_contents(ROOT / "data" / name)

    print("clean ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
