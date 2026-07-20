#!/usr/bin/env python3
"""Train one tuned model per pilot stock on real published data."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from stock_engine.config import load_config_with_hash
from stock_engine.models.per_stock_train import train_per_stock_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Per-ISIN walk-forward train + freeze (real pilot data only)",
    )
    parser.add_argument("--as-of", required=True, help="Feature/label as-of YYYY-MM-DD")
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-tune", action="store_true", help="Skip hyperparameter grid")
    args = parser.parse_args(argv)

    cfg, config_version, cfg_hash = load_config_with_hash()
    mcfg = dict(cfg.get("modeling", {}))
    if args.no_tune:
        mcfg["per_stock_tune"] = False
    root = args.data_root or Path(cfg.get("paths", {}).get("data_root", "data"))
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()

    result = train_per_stock_bundle(
        data_root=root,
        as_of_date=as_of,
        mcfg=mcfg,
        config_version=config_version,
        config_hash=cfg_hash,
        overwrite=args.overwrite,
    )
    print(f"status=success artifact={result['artifact_root']}")
    print(f"stocks={len(result['isins'])} rows={result['n_rows']}")
    for isin in result["isins"]:
        sm = result["stock_metrics"][isin]
        sym = sm["symbol"]
        auc_b = sm["summary"].get("auc_bullish_mean", float("nan"))
        auc_s = sm["summary"].get("auc_bearish_mean", float("nan"))
        print(f"stock.{sym} isin={isin} auc_bull={auc_b:.4f} auc_bear={auc_s:.4f}")
    print(json.dumps(result["stock_metrics"], indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
