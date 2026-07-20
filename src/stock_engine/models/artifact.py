"""Model artifact freeze / load (never silent overwrite)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib


def artifact_dir(
    models_root: Path,
    model_name: str,
    model_version: str,
    *,
    isin: str | None = None,
) -> Path:
    root = models_root / model_name / model_version
    if isin:
        return root / "by_isin" / isin
    return root


def publish_artifact(
    models_root: Path,
    *,
    model_name: str,
    model_version: str,
    bullish_model: Any,
    bearish_model: Any,
    feature_allowlist: list[str],
    train_manifest: dict[str, Any],
    metrics: dict[str, Any],
    overwrite: bool = False,
    isin: str | None = None,
) -> Path:
    root = artifact_dir(models_root, model_name, model_version, isin=isin)
    marker = root / "train_manifest.json"
    if marker.exists() and not overwrite:
        msg = (
            f"Refusing to overwrite existing model at {root}. "
            "Bump model_version or pass overwrite=True."
        )
        raise FileExistsError(msg)

    root.mkdir(parents=True, exist_ok=True)
    joblib.dump(bullish_model, root / "model_bullish.joblib")
    joblib.dump(bearish_model, root / "model_bearish.joblib")
    (root / "feature_allowlist.json").write_text(
        json.dumps(feature_allowlist, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "train_manifest.json").write_text(
        json.dumps(train_manifest, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    (root / "metrics_walkforward.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return root


def publish_per_stock_bundle(
    models_root: Path,
    *,
    model_name: str,
    model_version: str,
    feature_allowlist: list[str],
    bundle_manifest: dict[str, Any],
    stock_metrics: dict[str, Any],
    overwrite: bool = False,
) -> Path:
    """Write bundle manifest at model root (per-ISIN dirs already published)."""
    root = artifact_dir(models_root, model_name, model_version)
    marker = root / "bundle_manifest.json"
    if marker.exists() and not overwrite:
        msg = (
            f"Refusing to overwrite existing bundle at {root}. "
            "Bump model_version or pass overwrite=True."
        )
        raise FileExistsError(msg)
    root.mkdir(parents=True, exist_ok=True)
    (root / "bundle_manifest.json").write_text(
        json.dumps(bundle_manifest, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    (root / "feature_allowlist.json").write_text(
        json.dumps(feature_allowlist, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "metrics_per_stock.json").write_text(
        json.dumps(stock_metrics, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return root


def load_bundle_manifest(models_root: Path, model_name: str, model_version: str) -> dict[str, Any]:
    root = artifact_dir(models_root, model_name, model_version)
    path = root / "bundle_manifest.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def is_per_stock_bundle(models_root: Path, model_name: str, model_version: str) -> bool:
    manifest = load_bundle_manifest(models_root, model_name, model_version)
    return manifest.get("training_mode") == "per_stock"


def load_artifact(
    models_root: Path,
    model_name: str,
    model_version: str,
    *,
    isin: str | None = None,
) -> dict[str, Any]:
    if isin is None and is_per_stock_bundle(models_root, model_name, model_version):
        msg = "per_stock bundle requires isin= when loading a single model"
        raise ValueError(msg)

    root = artifact_dir(models_root, model_name, model_version, isin=isin)
    manifest_path = root / "train_manifest.json"
    if not manifest_path.exists():
        msg = f"Model artifact not found: {root}"
        raise FileNotFoundError(msg)
    allowlist = json.loads((root / "feature_allowlist.json").read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    metrics_path = root / "metrics_walkforward.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
    return {
        "root": root,
        "bullish_model": joblib.load(root / "model_bullish.joblib"),
        "bearish_model": joblib.load(root / "model_bearish.joblib"),
        "feature_allowlist": list(allowlist),
        "train_manifest": manifest,
        "metrics": metrics,
        "isin": isin,
    }
