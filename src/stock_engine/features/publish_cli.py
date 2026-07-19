"""CLI: stock-engine-publish-features."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from stock_engine.features.pipeline import run_feature_publish


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute and publish registered features from L1 inputs",
    )
    parser.add_argument(
        "--as-of",
        type=str,
        required=True,
        help="As-of date YYYY-MM-DD (must match published L1 partition)",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root (default: config paths.data_root)",
    )
    parser.add_argument(
        "--feature-set",
        type=str,
        default="core",
        help="Feature set name for store path (default: core)",
    )
    parser.add_argument(
        "--feature-version",
        type=str,
        default="v1",
        help="Feature set version for store path (default: v1)",
    )
    parser.add_argument(
        "--feature-id",
        action="append",
        default=None,
        help="Feature id name@version (repeatable; default: all registered computers)",
    )
    args = parser.parse_args(argv)

    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()
    result = run_feature_publish(
        data_root=args.data_root,
        as_of_date=as_of,
        feature_ids=args.feature_id,
        feature_set=args.feature_set,
        feature_version=args.feature_version,
    )
    print(
        f"status={result.status} run_id={result.run_id} "
        f"as_of={result.as_of_date} features={result.feature_ids}"
    )
    if result.manifest is not None:
        print(
            f"parquet={result.manifest.parquet_path} "
            f"content_hash={result.manifest.feature_content_hash[:12]}… "
            f"rows={result.manifest.row_count}"
        )
    for err in result.errors:
        print(f"error: {err}", file=sys.stderr)
    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
