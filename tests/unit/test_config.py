"""Unit tests for config loader."""

from pathlib import Path

from stock_engine.config import config_hash, load_config_with_hash


def test_default_config_loads(tmp_path: Path) -> None:
    default = tmp_path / "default.yaml"
    default.write_text(
        "config_version: '9.9.9'\nuniverse:\n  adv_min_inr_cr: 50\n",
        encoding="utf-8",
    )
    cfg, version, digest = load_config_with_hash(tmp_path, load_env_file=False)
    assert version == "9.9.9"
    assert cfg["universe"]["adv_min_inr_cr"] == 50
    assert digest == config_hash(cfg)
    assert len(digest) == 64


def test_local_overlay_wins(tmp_path: Path) -> None:
    (tmp_path / "default.yaml").write_text(
        "config_version: '0.1.0'\nuniverse:\n  adv_min_inr_cr: 50\n",
        encoding="utf-8",
    )
    (tmp_path / "local.yaml").write_text(
        "universe:\n  adv_min_inr_cr: 75\n",
        encoding="utf-8",
    )
    cfg, _, _ = load_config_with_hash(tmp_path, load_env_file=False)
    assert cfg["universe"]["adv_min_inr_cr"] == 75
