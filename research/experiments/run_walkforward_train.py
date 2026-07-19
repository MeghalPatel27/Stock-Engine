#!/usr/bin/env python3
"""Research entrypoint: purged expanding WF + freeze model artifact (PICK A)."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from stock_engine.config import load_config_with_hash
from stock_engine.models.artifact import publish_artifact
from stock_engine.models.io import load_train_matrix
from stock_engine.models.trainer import default_hgb_params
from stock_engine.models.walkforward import fit_final, run_walkforward


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Walk-forward train + freeze (research)")
    parser.add_argument("--as-of", required=True, help="Feature/label as-of YYYY-MM-DD")
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--feature-columns",
        type=str,
        default=None,
        help="Comma-separated feature column names (default: all non-key feature cols)",
    )
    args = parser.parse_args(argv)

    cfg, config_version, cfg_hash = load_config_with_hash()
    mcfg = cfg.get("modeling", {})
    root = args.data_root or Path(cfg.get("paths", {}).get("data_root", "data"))
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()

    matrix = load_train_matrix(
        root,
        as_of_date=as_of,
        feature_set=str(mcfg.get("feature_set", "core")),
        feature_version=str(mcfg.get("feature_version", "v1")),
        label_set=str(mcfg.get("label_set", "core")),
        label_version=str(mcfg.get("label_version", "v1")),
        horizon=int(mcfg.get("horizon", 5)),
    )
    if args.feature_columns:
        feature_columns = [c.strip() for c in args.feature_columns.split(",") if c.strip()]
    else:
        skip = {
            "isin",
            "session_date",
            "label",
            "forward_return",
            "sample_weight",
            "horizon",
            "label_version",
            "universe_mode",
            "label_source",
            "y_bullish",
            "y_bearish",
        }
        feature_columns = [c for c in matrix.columns if c not in skip]

    params = default_hgb_params(mcfg)
    wf = run_walkforward(
        matrix,
        feature_columns,
        horizon=int(mcfg.get("horizon", 5)),
        embargo_sessions=int(mcfg.get("embargo_sessions", 5)),
        min_train_sessions=int(mcfg.get("min_train_sessions", 60)),
        test_fold_sessions=int(mcfg.get("test_fold_sessions", 21)),
        step_sessions=int(mcfg.get("step_sessions", 21)),
        top_k=int(mcfg.get("top_k", 20)),
        risk_weight=float(mcfg.get("risk_weight", 1.0)),
        model_params=params,
    )

    bull, bear = fit_final(matrix, feature_columns, model_params=params)
    model_name = str(mcfg.get("model_name", "cs_quantile_h5"))
    model_version = str(mcfg.get("model_version", "v1"))
    manifest = {
        "model_name": model_name,
        "model_version": model_version,
        "config_version": config_version,
        "config_hash": cfg_hash,
        "as_of_date": as_of.isoformat(),
        "horizon": int(mcfg.get("horizon", 5)),
        "label_set": mcfg.get("label_set", "core"),
        "label_version": mcfg.get("label_version", "v1"),
        "feature_set": mcfg.get("feature_set", "core"),
        "feature_version": mcfg.get("feature_version", "v1"),
        "feature_allowlist": feature_columns,
        "risk_weight": float(mcfg.get("risk_weight", 1.0)),
        "embargo_sessions": int(mcfg.get("embargo_sessions", 5)),
        "train_window": "expanding",
        "heads": "independent_binary",
        "library": "sklearn.HistGradientBoostingClassifier",
        "params": params,
        "n_train_rows": int(len(matrix)),
        "n_sessions": int(matrix["session_date"].nunique()),
    }
    out = publish_artifact(
        root / "models",
        model_name=model_name,
        model_version=model_version,
        bullish_model=bull,
        bearish_model=bear,
        feature_allowlist=feature_columns,
        train_manifest=manifest,
        metrics=wf,
        overwrite=args.overwrite,
    )
    print(f"status=success artifact={out}")
    print(f"n_folds={wf['summary'].get('n_folds', 0)} rows={len(matrix)}")
    for k, v in sorted(wf["summary"].items()):
        print(f"metric.{k}={v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
