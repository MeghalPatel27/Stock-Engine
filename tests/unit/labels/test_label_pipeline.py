"""Label publish E2E tests."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from stock_engine.ingest.pipeline import run_ingest
from stock_engine.labels.hashing import label_content_hash
from stock_engine.labels.pipeline import run_label_publish
from stock_engine.labels.store import LocalParquetLabelStore

SHARED = Path(__file__).resolve().parents[2] / "fixtures" / "incoming"
LABEL_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "labels" / "incoming"
ALL = [
    "equity_eod.csv",
    "corporate_actions.csv",
    "symbol_isin_map.csv",
    "trading_calendar.csv",
]


def _stage(tmp_path: Path, fixture_dir: Path) -> Path:
    root = tmp_path / "data"
    incoming = root / "incoming"
    incoming.mkdir(parents=True)
    for name in ALL:
        shutil.copy(fixture_dir / name, incoming / name)
    for sub in ("raw", "clean", "metadata", "labels"):
        (root / sub).mkdir()
    return root


def test_e2e_ingest_then_publish_labels_nonempty(tmp_path: Path) -> None:
    """Dedicated fixtures: 5 names × 6 sessions → non-empty H=5 labels."""
    root = _stage(tmp_path, LABEL_FIXTURES)
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
    assert result.status == "success", result.errors
    assert result.manifest is not None
    assert result.manifest.row_count > 0
    assert result.manifest.universe_mode == "pilot"
    assert result.manifest.horizon == 5
    assert result.manifest.top_quantile == 0.20
    assert result.manifest.bottom_quantile == 0.20

    store = LocalParquetLabelStore(root / "labels")
    got = store.read(
        label_set="core",
        label_version="v1",
        horizon=5,
        as_of_date=published_as_of.isoformat(),
    )
    assert len(got) == result.manifest.row_count
    assert {"top_quantile", "bottom_quantile", "sample_weight", "label_source"} <= set(got.columns)
    assert set(got["label"]).issubset({"bullish", "bearish", "neutral"})
    # floor(5 * 0.20) = 1 → one bullish and one bearish per labeled session
    for _, g in got.groupby("session_date"):
        assert (g["label"] == "bullish").sum() == 1
        assert (g["label"] == "bearish").sum() == 1
        assert (g["label"] == "neutral").sum() == 3

    # Content hash is recomputable from published frame
    assert label_content_hash(got) == result.manifest.label_content_hash


def test_e2e_shared_fixtures_still_publish(tmp_path: Path) -> None:
    """Shared short fixtures may yield 0 H=5 rows; publish must still succeed."""
    root = _stage(tmp_path, SHARED)
    ingest = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert ingest.status == "success", ingest.errors
    published_as_of = date.fromisoformat(
        list((root / "clean" / "l1" / "equity_eod").glob("as_of_date=*"))[0].name.split("=", 1)[1]
    )
    result = run_label_publish(
        data_root=root,
        as_of_date=published_as_of,
        horizon=5,
        universe_mode="l1_intersection",
        overwrite=True,
    )
    assert result.status == "success", result.errors
    assert result.manifest is not None


def test_rejects_non_h5(tmp_path: Path) -> None:
    root = _stage(tmp_path, SHARED)
    result = run_label_publish(
        data_root=root,
        as_of_date=date(2026, 7, 18),
        horizon=20,
    )
    assert result.status == "failed"
    assert any("horizon=5" in e for e in result.errors)


def test_refuses_overwrite_by_default(tmp_path: Path) -> None:
    root = _stage(tmp_path, LABEL_FIXTURES)
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
