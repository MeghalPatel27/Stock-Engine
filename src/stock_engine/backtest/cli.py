"""CLI: stock-engine-backtest — purged WF paper backtest on published data."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from stock_engine.backtest.costs import DeliveryCostModel
from stock_engine.backtest.engine import run_walkforward_backtest
from stock_engine.config import load_config_with_hash


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Walk-forward paper backtest using published L1/features/labels only",
    )
    parser.add_argument("--as-of", required=True, help="Published as-of YYYY-MM-DD")
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument(
        "--out-dir", type=Path, default=None, help="Write metrics/trades JSON/Parquet"
    )
    args = parser.parse_args(argv)

    cfg, _, _ = load_config_with_hash()
    root = args.data_root or Path(cfg.get("paths", {}).get("data_root", "data"))
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()
    bcfg = cfg.get("backtest", {})
    mcfg = cfg.get("modeling", {})
    costs = DeliveryCostModel.from_config(bcfg.get("costs"))

    result = run_walkforward_backtest(
        data_root=root,
        as_of_date=as_of,
        horizon=int(mcfg.get("horizon", 5)),
        top_k=int(bcfg.get("top_k", cfg.get("output", {}).get("top_n_longs", 20))),
        risk_weight=float(mcfg.get("risk_weight", 1.0)),
        capital_inr=float(bcfg.get("capital_inr", 1_000_000)),
        cost_model=costs,
        modeling_cfg=mcfg,
        feature_set=str(mcfg.get("feature_set", "core")),
        feature_version=str(mcfg.get("feature_version", "v1")),
        label_set=str(mcfg.get("label_set", "core")),
        label_version=str(mcfg.get("label_version", "v1")),
    )

    print(f"status={result.status} as_of={result.as_of_date}")
    for err in result.errors:
        print(f"error: {err}", file=sys.stderr)
    for k, v in sorted(result.metrics.items()):
        print(f"metric.{k}={v}")

    if args.out_dir and result.status == "success":
        out = args.out_dir
        out.mkdir(parents=True, exist_ok=True)
        (out / "metrics.json").write_text(
            json.dumps(
                {
                    "metrics": result.metrics,
                    "fold_metrics": result.fold_metrics,
                    "cost_model": result.cost_model,
                    "as_of_date": result.as_of_date.isoformat(),
                },
                indent=2,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )
        if result.trades is not None:
            result.trades.to_parquet(out / "trades.parquet", index=False)
        if result.period_returns is not None:
            result.period_returns.to_parquet(out / "period_returns.parquet", index=False)
        print(f"wrote={out}")

    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
