"""Model artifact freeze / load (never silent overwrite)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib


def artifact_dir(models_root: Path, model_name: str, model_version: str) -> Path:
    return models_root / model_name / model_version


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
) -> Path:
    root = artifact_dir(models_root, model_name, model_version)
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


def load_artifact(models_root: Path, model_name: str, model_version: str) -> dict[str, Any]:
    root = artifact_dir(models_root, model_name, model_version)
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
    }
