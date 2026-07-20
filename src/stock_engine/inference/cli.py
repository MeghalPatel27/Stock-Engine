"""CLI: stock-engine-infer — publish daily RankRows from frozen model."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from stock_engine.inference.pipeline import run_inference_publish


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Score published features with frozen model and publish RankRows",
    )
    parser.add_argument("--as-of", required=True, help="As-of date YYYY-MM-DD")
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument(
        "--session-date",
        type=str,
        default=None,
        help="Decision session (default: as-of)",
    )
    parser.add_argument("--rank-set", type=str, default="core")
    parser.add_argument("--rank-version", type=str, default="v1")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing as_of partition",
    )
    args = parser.parse_args(argv)

    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()
    session = datetime.strptime(args.session_date, "%Y-%m-%d").date() if args.session_date else None
    result = run_inference_publish(
        data_root=args.data_root,
        as_of_date=as_of,
        session_date=session,
        rank_set=args.rank_set,
        rank_version=args.rank_version,
        overwrite=args.overwrite,
    )
    print(
        f"status={result.status} run_id={result.run_id} "
        f"as_of={result.as_of_date} session={result.session_date}"
    )
    if result.manifest is not None:
        print(
            f"parquet={result.manifest.parquet_path} "
            f"rows={result.manifest.row_count} "
            f"model={result.manifest.model_name}/{result.manifest.model_version}"
        )
        print(f"top_longs={','.join(result.top_longs)}")
        print(f"top_shorts={','.join(result.top_shorts)}")
    for err in result.errors:
        print(f"error: {err}", file=sys.stderr)
    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
