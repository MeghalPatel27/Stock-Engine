"""CLI smoke for stock-engine-publish-labels."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from stock_engine.ingest.pipeline import run_ingest
from stock_engine.labels.cli import main

LABEL_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "labels" / "incoming"
ALL = [
    "equity_eod.csv",
    "corporate_actions.csv",
    "symbol_isin_map.csv",
    "trading_calendar.csv",
]


def test_cli_publish_labels(tmp_path: Path, capsys) -> None:
    root = tmp_path / "data"
    incoming = root / "incoming"
    incoming.mkdir(parents=True)
    for name in ALL:
        shutil.copy(LABEL_FIXTURES / name, incoming / name)
    for sub in ("raw", "clean", "metadata", "labels"):
        (root / sub).mkdir()

    ingest = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert ingest.status == "success", ingest.errors
    as_of = list((root / "clean" / "l1" / "equity_eod").glob("as_of_date=*"))[0].name.split("=", 1)[
        1
    ]

    code = main(
        [
            "--as-of",
            as_of,
            "--data-root",
            str(root),
            "--universe-mode",
            "pilot",
            "--overwrite",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "status=success" in captured.out
    assert "rows=" in captured.out
