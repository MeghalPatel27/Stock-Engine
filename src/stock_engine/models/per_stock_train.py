"""Train and freeze one model per ISIN (pilot-quality mode)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from stock_engine.models.artifact import publish_artifact, publish_per_stock_bundle
from stock_engine.models.io import load_symbol_map_from_l1, load_train_matrix
from stock_engine.models.per_stock import train_one_stock


def _feature_columns(matrix: pd.DataFrame) -> list[str]:
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
    cols = [c for c in matrix.columns if c not in skip]
    if not cols:
        msg = "no feature columns in train matrix"
        raise ValueError(msg)
    return cols


def train_per_stock_bundle(
    *,
    data_root: Path,
    as_of_date: date,
    mcfg: dict[str, Any],
    config_version: str,
    config_hash: str,
    overwrite: bool = False,
) -> dict[str, Any]:
    """
    Train, evaluate, and freeze one two-head model per ISIN on real published data.
    """
    matrix = load_train_matrix(
        data_root,
        as_of_date=as_of_date,
        feature_set=str(mcfg.get("feature_set", "core")),
        feature_version=str(mcfg.get("feature_version", "v1")),
        label_set=str(mcfg.get("label_set", "core")),
        label_version=str(mcfg.get("label_version", "v1")),
        horizon=int(mcfg.get("horizon", 5)),
    )
    feature_columns = _feature_columns(matrix)
    symbol_map = load_symbol_map_from_l1(data_root, as_of_date)
    tune = bool(mcfg.get("per_stock_tune", True))

    model_name = str(mcfg.get("model_name", "cs_quantile_h5_per_stock"))
    model_version = str(mcfg.get("model_version", "v1"))
    models_root = data_root / "models"

    stock_metrics: dict[str, Any] = {}
    isins_trained: list[str] = []

    for isin in sorted(matrix["isin"].astype(str).unique()):
        sub = matrix.loc[matrix["isin"].astype(str) == isin].copy()
        symbol = symbol_map.get(isin, isin)
        print(f"training isin={isin} symbol={symbol} rows={len(sub)}", flush=True)
        bull, bear, wf, smanifest = train_one_stock(
            sub,
            feature_columns,
            isin=isin,
            symbol=symbol,
            mcfg=mcfg,
            tune=tune,
        )
        stock_manifest = {
            **smanifest,
            "model_name": model_name,
            "model_version": model_version,
            "config_version": config_version,
            "config_hash": config_hash,
            "as_of_date": as_of_date.isoformat(),
            "horizon": int(mcfg.get("horizon", 5)),
            "feature_set": mcfg.get("feature_set", "core"),
            "feature_version": mcfg.get("feature_version", "v1"),
            "label_set": mcfg.get("label_set", "core"),
            "label_version": mcfg.get("label_version", "v1"),
            "feature_allowlist": feature_columns,
            "risk_weight": float(mcfg.get("risk_weight", 1.0)),
        }
        publish_artifact(
            models_root,
            model_name=model_name,
            model_version=model_version,
            bullish_model=bull,
            bearish_model=bear,
            feature_allowlist=feature_columns,
            train_manifest=stock_manifest,
            metrics=wf,
            overwrite=overwrite,
            isin=isin,
        )
        stock_metrics[isin] = {
            "symbol": symbol,
            "summary": wf.get("summary", {}),
            "params": smanifest.get("params"),
            "tune_val_score": smanifest.get("tune_val_score"),
        }
        isins_trained.append(isin)

    bundle_manifest = {
        "training_mode": "per_stock",
        "model_name": model_name,
        "model_version": model_version,
        "config_version": config_version,
        "config_hash": config_hash,
        "as_of_date": as_of_date.isoformat(),
        "horizon": int(mcfg.get("horizon", 5)),
        "isins": isins_trained,
        "feature_allowlist": feature_columns,
        "n_stocks": len(isins_trained),
        "n_total_rows": int(len(matrix)),
    }
    root = publish_per_stock_bundle(
        models_root,
        model_name=model_name,
        model_version=model_version,
        feature_allowlist=feature_columns,
        bundle_manifest=bundle_manifest,
        stock_metrics=stock_metrics,
        overwrite=overwrite,
    )
    return {
        "artifact_root": str(root),
        "isins": isins_trained,
        "stock_metrics": stock_metrics,
        "n_rows": int(len(matrix)),
    }
