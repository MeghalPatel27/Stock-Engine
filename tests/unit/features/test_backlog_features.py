"""Coverage for planned backlog feature families."""

from __future__ import annotations

import shutil
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from stock_engine.features.compute import FEATURE_COMPUTERS
from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.compute.cs import compute_cs_zscore_mom_ret_5d
from stock_engine.features.compute.mom_ret import compute_mom_ret_5d
from stock_engine.features.compute.raw_close_adj import compute_raw_close_adj_l1
from stock_engine.features.compute.trend import (
    compute_trend_ema_20,
    compute_trend_price_vs_ema_20,
)
from stock_engine.features.compute.vol import compute_vol_std_20d
from stock_engine.features.pipeline import run_feature_publish
from stock_engine.features.registry import load_registry
from stock_engine.ingest.pipeline import run_ingest

REPO = Path(__file__).resolve().parents[3]
FIXTURES_INCOMING = Path(__file__).resolve().parents[2] / "fixtures" / "incoming"
ALL = [
    "equity_eod.csv",
    "corporate_actions.csv",
    "symbol_isin_map.csv",
    "trading_calendar.csv",
]


def _registry():
    return load_registry(
        REPO / "docs" / "features" / "registry",
        REPO / "docs" / "features" / "families.yaml",
        datasets_path=REPO / "docs" / "features" / "datasets.yaml",
    )


def test_registry_matches_computers() -> None:
    registry = _registry()
    reg_ids = {f.feature_id for f in registry.all()}
    assert reg_ids == set(FEATURE_COMPUTERS)
    assert len(FEATURE_COMPUTERS) == 25


def test_trend_price_vs_ema() -> None:
    registry = _registry()
    days = [pd.Timestamp(date(2026, 1, 1) + timedelta(days=i)) for i in range(25)]
    sessions = pd.DatetimeIndex(days)
    closes = [100.0 + i for i in range(25)]
    l1 = pd.DataFrame({"isin": ["INE001"] * 25, "session_date": sessions, "close_adj": closes})
    ctx = ComputeContext(as_of_date=sessions[-1].date(), l1_equity=l1, open_sessions=sessions)
    ctx.features["raw__close_adj__l1@v1"] = compute_raw_close_adj_l1(
        ctx, registry.get("raw__close_adj__l1", "v1")
    )
    ctx.features["trend__ema__20@v1"] = compute_trend_ema_20(
        ctx, registry.get("trend__ema__20", "v1")
    )
    out = compute_trend_price_vs_ema_20(ctx, registry.get("trend__price_vs_ema__20", "v1"))
    assert out["trend__price_vs_ema__20"].notna().any()
    last = out.dropna().iloc[-1]
    close = float(
        ctx.features["raw__close_adj__l1@v1"]
        .set_index("session_date")
        .loc[last["session_date"], "raw__close_adj__l1"]
    )
    ema = float(
        ctx.features["trend__ema__20@v1"]
        .set_index("session_date")
        .loc[last["session_date"], "trend__ema__20"]
    )
    assert abs(float(last["trend__price_vs_ema__20"]) - (close / ema - 1)) < 1e-10


def test_vol_std_and_cs_zscore() -> None:
    registry = _registry()
    days = [pd.Timestamp(date(2026, 1, 1) + timedelta(days=i)) for i in range(30)]
    sessions = pd.DatetimeIndex(days)
    # two names, trending vs flat
    rows = []
    for i, s in enumerate(sessions):
        rows.append({"isin": "INE001", "session_date": s, "close_adj": 100.0 + i})
        rows.append({"isin": "INE002", "session_date": s, "close_adj": 100.0})
    l1 = pd.DataFrame(rows)
    ctx = ComputeContext(as_of_date=sessions[-1].date(), l1_equity=l1, open_sessions=sessions)
    ctx.features["raw__close_adj__l1@v1"] = compute_raw_close_adj_l1(
        ctx, registry.get("raw__close_adj__l1", "v1")
    )
    ctx.features["mom__ret__1d@v1"] = __import__(
        "stock_engine.features.compute.mom_ret", fromlist=["compute_mom_ret_1d"]
    ).compute_mom_ret_1d(ctx, registry.get("mom__ret__1d", "v1"))
    ctx.features["mom__ret__5d@v1"] = compute_mom_ret_5d(ctx, registry.get("mom__ret__5d", "v1"))
    ctx.features["vol__std__20d@v1"] = compute_vol_std_20d(ctx, registry.get("vol__std__20d", "v1"))
    assert ctx.features["vol__std__20d@v1"]["vol__std__20d"].notna().any()

    cs = compute_cs_zscore_mom_ret_5d(ctx, registry.get("cs__zscore__mom__ret__5d", "v1"))
    # On last date with both names non-null, z-scores should sum ~ 0
    last = cs["session_date"].max()
    day = cs[(cs["session_date"] == last) & cs["cs__zscore__mom__ret__5d"].notna()]
    if len(day) >= 2:
        assert abs(day["cs__zscore__mom__ret__5d"].sum()) < 1e-10


def test_e2e_publish_all_features(tmp_path: Path) -> None:
    root = tmp_path / "data"
    incoming = root / "incoming"
    incoming.mkdir(parents=True)
    for name in ALL:
        shutil.copy(FIXTURES_INCOMING / name, incoming / name)
    for sub in ("raw", "clean", "metadata", "features"):
        (root / sub).mkdir()

    ingest = run_ingest(data_root=root, as_of_date=date(2026, 7, 18))
    assert ingest.status == "success", ingest.errors
    published_as_of = date.fromisoformat(
        list((root / "clean" / "l1" / "equity_eod").glob("as_of_date=*"))[0].name.split("=", 1)[1]
    )

    result = run_feature_publish(
        data_root=root,
        as_of_date=published_as_of,
        feature_set="core",
        feature_version="v1",
        repo_root=REPO,
    )
    assert result.status == "success", result.errors
    assert len(result.feature_ids) == 25
