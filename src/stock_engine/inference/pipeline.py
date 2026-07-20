"""End-to-end inference publish: frozen model → RankRows (no labels)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.config import load_config_with_hash
from stock_engine.contracts.rank_row import RankRow
from stock_engine.features.hashing import feature_content_hash
from stock_engine.inference.models import RankSetManifest
from stock_engine.inference.signals import signals_from_rank_frame
from stock_engine.inference.store import LocalParquetRankStore
from stock_engine.inference.validate import validate_rank_frame
from stock_engine.logging_utils import configure_logging
from stock_engine.models.io import load_symbol_map_from_l1
from stock_engine.models.ranking import score_long, score_short
from stock_engine.models.scorer import score_published_features


@dataclass
class InferenceRunResult:
    run_id: str
    as_of_date: date
    session_date: date
    config_version: str
    config_hash: str
    status: str
    manifest: RankSetManifest | None = None
    top_longs: list[str] = field(default_factory=list)
    top_shorts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _rank_rows_to_frame(
    rows: list[RankRow],
    *,
    symbol_to_isin: dict[str, str],
    session_date: date,
    risk_weight: float,
) -> pd.DataFrame:
    records = []
    for r in rows:
        isin = symbol_to_isin.get(r.symbol, r.symbol)
        s_long = float(score_long(r.p_bullish, r.confidence, r.risk, risk_weight=risk_weight))
        s_short = float(score_short(r.p_bearish, r.confidence, r.risk, risk_weight=risk_weight))
        records.append(
            {
                "symbol": r.symbol,
                "isin": isin,
                "as_of_date": r.as_of_date.isoformat(),
                "session_date": session_date.isoformat(),
                "horizon": r.horizon,
                "p_bullish": r.p_bullish,
                "p_bearish": r.p_bearish,
                "p_neutral": r.p_neutral,
                "risk": r.risk,
                "confidence": r.confidence,
                "score_long": s_long,
                "score_short": s_short,
                "rank_long": r.rank_long,
                "rank_short": r.rank_short,
                "model_version": r.model_version,
                "config_version": r.config_version,
            }
        )
    return pd.DataFrame.from_records(records)


def run_inference_publish(
    *,
    data_root: Path | None = None,
    as_of_date: date,
    session_date: date | None = None,
    rank_set: str = "core",
    rank_version: str = "v1",
    overwrite: bool = False,
    config_dir: Path | None = None,
) -> InferenceRunResult:
    cfg, config_version, cfg_hash = load_config_with_hash(config_dir)
    root = data_root or Path(cfg.get("paths", {}).get("data_root", "data"))
    mcfg = cfg.get("modeling", {})
    out_cfg = cfg.get("output", {})

    decision = session_date or as_of_date
    model_name = str(mcfg.get("model_name", "cs_quantile_h5"))
    model_version = str(mcfg.get("model_version", "v1"))
    horizon = int(mcfg.get("horizon", 5))
    risk_weight = float(mcfg.get("risk_weight", 1.0))
    feature_set = str(mcfg.get("feature_set", "core"))
    feature_version = str(mcfg.get("feature_version", "v1"))
    top_n_longs = int(out_cfg.get("top_n_longs", 20))
    top_n_shorts = int(out_cfg.get("top_n_shorts", 20))

    run_id = configure_logging(pipeline_stage="inference")
    result = InferenceRunResult(
        run_id=run_id,
        as_of_date=as_of_date,
        session_date=decision,
        config_version=config_version,
        config_hash=cfg_hash,
        status="failed",
    )

    try:
        rows = score_published_features(
            root,
            as_of_date=as_of_date,
            model_name=model_name,
            model_version=model_version,
            feature_set=feature_set,
            feature_version=feature_version,
            risk_weight=risk_weight,
            config_version=config_version,
            horizon=horizon,
            session_date=decision,
        )
        if not rows:
            result.errors.append("scorer returned no RankRows")
            return result

        # Map symbol → isin from L1 (scorer may fall back to ISIN as symbol)
        isin_to_symbol = load_symbol_map_from_l1(root, as_of_date)
        symbol_to_isin = {v: k for k, v in isin_to_symbol.items()}
        for isin in isin_to_symbol:
            symbol_to_isin.setdefault(isin, isin)

        frame = _rank_rows_to_frame(
            rows,
            symbol_to_isin=symbol_to_isin,
            session_date=decision,
            risk_weight=risk_weight,
        )
        errors = validate_rank_frame(frame, horizon=horizon, model_version=model_version)
        if errors:
            result.errors.extend(errors)
            return result

        store = LocalParquetRankStore(root / "ranks")
        path = store.write(
            frame,
            rank_set=rank_set,
            rank_version=rank_version,
            horizon=horizon,
            as_of_date=as_of_date.isoformat(),
            overwrite=overwrite,
        )
        content_hash = feature_content_hash(frame)

        meta_dir = root / "metadata" / "ranks" / "published" / as_of_date.isoformat()
        meta_dir.mkdir(parents=True, exist_ok=True)
        manifest = RankSetManifest(
            run_id=run_id,
            as_of_date=as_of_date,
            session_date=decision,
            config_version=config_version,
            config_hash=cfg_hash,
            rank_set=rank_set,
            rank_version=rank_version,
            horizon=horizon,
            model_name=model_name,
            model_version=model_version,
            feature_set=feature_set,
            feature_version=feature_version,
            risk_weight=risk_weight,
            row_count=len(frame),
            top_n_longs=top_n_longs,
            top_n_shorts=top_n_shorts,
            parquet_path=str(path),
            content_hash=content_hash,
        )
        meta_path = meta_dir / f"{rank_set}__{rank_version}__h{horizon}.json"
        meta_path.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        # Optional signals sidecar (not required for RankRow consumers)
        signals = signals_from_rank_frame(frame, model_version=model_version)
        signals_path = path.parent / "signals.json"
        signals_path.write_text(
            json.dumps([s.model_dump(mode="json") for s in signals], indent=2) + "\n",
            encoding="utf-8",
        )

        top_longs = (
            frame.sort_values(["rank_long", "symbol"])
            .head(min(top_n_longs, len(frame)))["symbol"]
            .tolist()
        )
        top_shorts = (
            frame.sort_values(["rank_short", "symbol"])
            .head(min(top_n_shorts, len(frame)))["symbol"]
            .tolist()
        )

        result.status = "success"
        result.manifest = manifest
        result.top_longs = top_longs
        result.top_shorts = top_shorts
        return result
    except FileExistsError as exc:
        result.errors.append(str(exc))
        return result
    except (FileNotFoundError, ValueError, OSError) as exc:
        result.errors.append(str(exc))
        return result
