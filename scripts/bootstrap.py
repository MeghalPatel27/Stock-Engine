#!/usr/bin/env python3
"""Create local data directories and verify config loads. Not production pipeline code."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stock_engine.config import load_config_with_hash  # noqa: E402


def main() -> int:
    data_root = ROOT / "data"
    for name in ("raw", "clean", "features", "metadata"):
        (data_root / name).mkdir(parents=True, exist_ok=True)
        keep = data_root / name / ".gitkeep"
        if not keep.exists():
            keep.touch()

    cfg, version, digest = load_config_with_hash()
    print(f"bootstrap ok config_version={version} config_hash={digest[:12]}…")
    print(f"keys={sorted(cfg.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
