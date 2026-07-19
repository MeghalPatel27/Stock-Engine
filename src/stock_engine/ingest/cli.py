"""CLI entrypoint for local CSV ingest."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from stock_engine.ingest.pipeline import run_ingest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ingest local CSVs from data/incoming into raw + clean Parquet",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root (default: config paths.data_root)",
    )
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="As-of date YYYY-MM-DD (default: max session_date in equity_eod)",
    )
    parser.add_argument(
        "--dataset-version",
        type=str,
        default=None,
        help="Dataset version string (default: vYYYYMMDD from as-of)",
    )
    args = parser.parse_args(argv)

    as_of = None
    if args.as_of:
        as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()

    result = run_ingest(
        data_root=args.data_root,
        as_of_date=as_of,
        dataset_version=args.dataset_version,
    )
    print(
        f"status={result.status} run_id={result.run_id} "
        f"as_of={result.as_of_date} config_hash={result.config_hash[:12]}… "
        f"dataset_version={result.dataset_version}"
    )
    for warn in result.warnings:
        print(f"warning: {warn}", file=sys.stderr)
    if result.errors:
        for err in result.errors:
            print(f"error: {err}", file=sys.stderr)
    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
