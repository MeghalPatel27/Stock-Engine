"""Label publish E2E tests."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from stock_engine.ingest.pipeline import run_ingest
from stock_engine.labels.pipeline import run_label_publish
from stock_engine.labels.store import LocalParquetLabelStore

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "incoming"
ALL = [
    "equity_eod.csv",
    "corporate_actions.csv",
    "symbol_isin_map.csv",
    "trading_calendar.csv",
]


def _stage(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    incoming = root / "incoming"
    incoming.mkdir(parents=True)
    for name in ALL:
        shutil.copy(FIXTURES / name, incoming / name)
    for sub in ("raw", "clean", "metadata", "labels"):
        (root / sub).mkdir()
    return root


def test_e2e_ingest_then_publish_labels(tmp_path: Path) -> None:
    root = _stage(tmp_path)
    ingest = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert ingest.status == "success", ingest.errors
    published_as_of = date.fromisoformat(
        list((root / "clean" / "l1" / "equity_eod").glob("as_of_date=*"))[0].name.split("=", 1)[1]
    )

    result = run_label_publish(
        data_root=root,
        as_of_date=published_as_of,
        horizon=5,
        universe_mode="pilot",
        overwrite=True,
    )
    # Fixture history is short (~5 sessions) → may yield 0 label rows if H=5
    # Still must succeed with empty or non-empty frame
    assert result.status == "success", result.errors
    assert result.manifest is not None
    assert result.manifest.universe_mode == "pilot"
    assert "top_quantile" in result.manifest.model_dump()

    store = LocalParquetLabelStore(root / "labels")
    if result.manifest.row_count > 0:
        got = store.read(
            label_set="core",
            label_version="v1",
            horizon=5,
            as_of_date=published_as_of.isoformat(),
        )
        assert "top_quantile" in got.columns
        assert "bottom_quantile" in got.columns
        assert set(got["label"]).issubset({"bullish", "bearish", "neutral"})


def test_rejects_non_h5(tmp_path: Path) -> None:
    root = _stage(tmp_path)
    result = run_label_publish(
        data_root=root,
        as_of_date=date(2026, 7, 18),
        horizon=20,
    )
    assert result.status == "failed"
    assert any("horizon=5" in e for e in result.errors)


def test_refuses_overwrite_by_default(tmp_path: Path) -> None:
    root = _stage(tmp_path)
    ingest = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert ingest.status == "success", ingest.errors
    published_as_of = date.fromisoformat(
        list((root / "clean" / "l1" / "equity_eod").glob("as_of_date=*"))[0].name.split("=", 1)[1]
    )
    first = run_label_publish(data_root=root, as_of_date=published_as_of, overwrite=True)
    assert first.status == "success", first.errors
    second = run_label_publish(data_root=root, as_of_date=published_as_of, overwrite=False)
    assert second.status == "failed"
    assert any("overwrite" in e.lower() or "Refusing" in e for e in second.errors)
