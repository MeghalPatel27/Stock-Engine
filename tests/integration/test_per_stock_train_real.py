"""Integration: per-stock bundle trains on real pilot when data present."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from stock_engine.config import load_config_with_hash
from stock_engine.models.artifact import is_per_stock_bundle, load_artifact
from stock_engine.models.per_stock_train import train_per_stock_bundle

DATA = Path(__file__).resolve().parents[2] / "data"
AS_OF = date(2026, 7, 17)


def _ready() -> bool:
    return (
        DATA / "features" / "core" / "v1" / f"as_of_date={AS_OF}" / "features.parquet"
    ).exists() and (
        DATA / "labels" / "core" / "v1" / "horizon=5" / f"as_of_date={AS_OF}" / "labels.parquet"
    ).exists()


@pytest.mark.skipif(not _ready(), reason="published pilot data not present")
def test_per_stock_bundle_on_real_pilot(tmp_path: Path) -> None:
    cfg, config_version, cfg_hash = load_config_with_hash()
    mcfg = dict(cfg.get("modeling", {}))
    mcfg["per_stock_tune"] = False  # fast CI
    mcfg["max_iter"] = 50
    mcfg["min_train_sessions"] = 120
    mcfg["per_stock_step_sessions"] = 84
    mcfg["model_name"] = "test_per_stock"
    mcfg["model_version"] = "v1"

    root = tmp_path / "data"
    # Copy published partitions into tmp (read-only source)
    import shutil

    for part in ("features", "labels", "clean"):
        shutil.copytree(DATA / part, root / part, dirs_exist_ok=True)

    result = train_per_stock_bundle(
        data_root=root,
        as_of_date=AS_OF,
        mcfg=mcfg,
        config_version=config_version,
        config_hash=cfg_hash,
        overwrite=True,
    )
    assert len(result["isins"]) == 5
    assert is_per_stock_bundle(root / "models", "test_per_stock", "v1")
    art = load_artifact(root / "models", "test_per_stock", "v1", isin=result["isins"][0])
    assert art["feature_allowlist"]
