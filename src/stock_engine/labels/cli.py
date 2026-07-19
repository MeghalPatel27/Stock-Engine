"""CLI: stock-engine-publish-labels."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from stock_engine.labels.pipeline import run_label_publish


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute and publish cross-sectional labels from L1 (H=5 V1)",
    )
    parser.add_argument("--as-of", type=str, required=True, help="As-of date YYYY-MM-DD")
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--horizon", type=int, default=None, help="Must be 5 in V1")
    parser.add_argument("--label-set", type=str, default="core")
    parser.add_argument("--label-version", type=str, default="v1")
    parser.add_argument(
        "--universe-mode",
        type=str,
        default=None,
        choices=["pilot", "l1_intersection", "phase1_filters"],
    )
    parser.add_argument(
        "--selection-policy",
        type=str,
        default=None,
        choices=["floor", "ceil", "nearest"],
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing as_of partition (same version)",
    )
    args = parser.parse_args(argv)

    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()
    result = run_label_publish(
        data_root=args.data_root,
        as_of_date=as_of,
        horizon=args.horizon,
        label_set=args.label_set,
        label_version=args.label_version,
        universe_mode=args.universe_mode,
        selection_policy=args.selection_policy,
        overwrite=args.overwrite,
    )
    print(
        f"status={result.status} run_id={result.run_id} "
        f"as_of={result.as_of_date} horizon={result.horizon}"
    )
    if result.manifest is not None:
        print(
            f"parquet={result.manifest.parquet_path} "
            f"rows={result.manifest.row_count} "
            f"mode={result.manifest.universe_mode} "
            f"content_hash={result.manifest.label_content_hash[:12]}…"
        )
    for err in result.errors:
        print(f"error: {err}", file=sys.stderr)
    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
