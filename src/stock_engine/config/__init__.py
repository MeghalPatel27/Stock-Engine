"""Config load/merge and hashing for reproducibility."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

DEFAULT_CONFIG_VERSION = "0.1.0"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        msg = f"Config root must be a mapping: {path}"
        raise ValueError(msg)
    return data


def config_hash(config: dict[str, Any]) -> str:
    """Stable hash of effective config (canonical JSON)."""
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_config(
    config_dir: Path | None = None,
    *,
    load_env_file: bool = True,
) -> dict[str, Any]:
    """
    Load effective config: default.yaml < local.yaml < env path overrides.

    Always ensures `config_version` is present.
    """
    if load_env_file:
        load_dotenv(_repo_root() / ".env", override=False)

    root = config_dir or (_repo_root() / "config")
    merged = _deep_merge(_load_yaml(root / "default.yaml"), _load_yaml(root / "local.yaml"))

    data_root = os.getenv("STOCK_ENGINE_DATA_ROOT")
    if data_root:
        paths = dict(merged.get("paths") or {})
        paths["data_root"] = data_root
        merged["paths"] = paths

    merged.setdefault("config_version", DEFAULT_CONFIG_VERSION)
    return merged


def load_config_with_hash(
    config_dir: Path | None = None,
    *,
    load_env_file: bool = True,
) -> tuple[dict[str, Any], str, str]:
    """Return (config, config_version, config_hash)."""
    cfg = load_config(config_dir, load_env_file=load_env_file)
    version = str(cfg.get("config_version", DEFAULT_CONFIG_VERSION))
    return cfg, version, config_hash(cfg)
