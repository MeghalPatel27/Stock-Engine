"""CLI: stock-engine-score — load frozen model, emit RankRows (no labels)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from stock_engine.config import load_config_with_hash
from stock_engine.models.scorer import score_published_features


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Score published features with a frozen model → RankRow JSON",
    )
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--model-name", type=str, default=None)
    parser.add_argument("--model-version", type=str, default=None)
    parser.add_argument(
        "--session-date", type=str, default=None, help="Decision session (default as-of)"
    )
    parser.add_argument("--out", type=Path, default=None, help="Write JSON lines; default stdout")
    args = parser.parse_args(argv)

    cfg, config_version, _ = load_config_with_hash()
    mcfg = cfg.get("modeling", {})
    root = args.data_root or Path(cfg.get("paths", {}).get("data_root", "data"))
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()
    session = datetime.strptime(args.session_date, "%Y-%m-%d").date() if args.session_date else None

    rows = score_published_features(
        root,
        as_of_date=as_of,
        model_name=args.model_name or str(mcfg.get("model_name", "cs_quantile_h5")),
        model_version=args.model_version or str(mcfg.get("model_version", "v1")),
        feature_set=str(mcfg.get("feature_set", "core")),
        feature_version=str(mcfg.get("feature_version", "v1")),
        risk_weight=float(mcfg.get("risk_weight", 1.0)),
        config_version=config_version,
        horizon=int(mcfg.get("horizon", 5)),
        session_date=session,
    )
    payload = [r.model_dump(mode="json") for r in rows]
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"status=success n={len(rows)} out={args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
