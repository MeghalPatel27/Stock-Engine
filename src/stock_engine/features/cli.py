"""CLI: stock-engine-lint-features."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stock_engine.features.lint import lint_feature_registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint feature registry (schema, families, DAG, dataset deps)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: cwd)",
    )
    args = parser.parse_args(argv)

    errors = lint_feature_registry(args.repo_root.resolve())
    if errors:
        print("Feature registry lint FAILED:", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 1

    print("Feature registry lint OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
