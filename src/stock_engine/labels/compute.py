"""H-session cross-sectional label assignment from L1 adjusted closes."""

from __future__ import annotations

import math
from datetime import date
from typing import Literal

import pandas as pd

from stock_engine.features.calendar import open_sessions, session_after
from stock_engine.labels.quantiles import top_bottom_sizes

UniverseMode = Literal["pilot", "l1_intersection", "phase1_filters"]
SelectionPolicy = Literal["floor", "ceil", "nearest"]

LABEL_COLUMNS = (
    "isin",
    "session_date",
    "horizon",
    "forward_return",
    "label",
    "universe_size",
    "label_version",
    "universe_mode",
    "selection_policy",
    "top_quantile",
    "bottom_quantile",
    "sample_weight",
    "label_source",
)


def _resolve_universe_isins(
    panel: pd.DataFrame,
    *,
    universe_mode: UniverseMode,
    pilot_isins: list[str] | None,
) -> set[str]:
    all_isins = set(panel["isin"].astype(str).unique())
    if universe_mode == "phase1_filters":
        msg = (
            "universe_mode=phase1_filters is not implemented yet "
            "(requires weekly F&O membership + ADV/price filters)"
        )
        raise NotImplementedError(msg)
    if universe_mode == "pilot":
        if pilot_isins:
            allowed = set(pilot_isins)
            return all_isins & allowed
        # Empty pilot_isins: all L1 names, but still tagged pilot (not for prod benchmarks)
        return all_isins
    if universe_mode == "l1_intersection":
        return all_isins
    msg = f"Unknown universe_mode: {universe_mode}"
    raise ValueError(msg)


def compute_forward_returns(
    l1_equity: pd.DataFrame,
    open_calendar: pd.DatetimeIndex,
    *,
    horizon: int,
    as_of_date: date,
) -> pd.DataFrame:
    """
    Build rows (isin, session_date, forward_return) for all T with T+H known
    and T+H <= as_of_date.
    """
    if horizon < 1:
        msg = "horizon must be >= 1"
        raise ValueError(msg)
    required = {"isin", "session_date", "close_adj"}
    missing = required - set(l1_equity.columns)
    if missing:
        msg = f"L1 missing columns: {sorted(missing)}"
        raise ValueError(msg)

    sessions = open_sessions(open_calendar)
    cutoff = pd.Timestamp(as_of_date).normalize()
    sessions = sessions[sessions <= cutoff]

    src = l1_equity[["isin", "session_date", "close_adj"]].copy()
    src["isin"] = src["isin"].astype(str)
    src["session_date"] = pd.to_datetime(src["session_date"]).dt.normalize()
    src["close_adj"] = pd.to_numeric(src["close_adj"], errors="coerce")
    src = src.dropna(subset=["close_adj"])
    src = src.loc[src["session_date"].isin(set(sessions))]

    # Map isin -> session -> close
    close_map: dict[str, dict[pd.Timestamp, float]] = {}
    for isin, g in src.groupby("isin", sort=False):
        close_map[str(isin)] = dict(
            zip(g["session_date"], g["close_adj"].astype(float), strict=False)
        )

    rows: list[dict[str, object]] = []
    session_list = list(sessions)
    for t in session_list:
        t_h = session_after(sessions, t, offset=horizon)
        if t_h is None or t_h > cutoff:
            continue
        for isin, cmap in close_map.items():
            c0 = cmap.get(t)
            c1 = cmap.get(t_h)
            if c0 is None or c1 is None or c0 == 0:
                continue
            rows.append(
                {
                    "isin": isin,
                    "session_date": t,
                    "forward_return": float(c1 / c0 - 1.0),
                }
            )

    if not rows:
        return pd.DataFrame(columns=["isin", "session_date", "forward_return"])
    out = pd.DataFrame(rows)
    return out.sort_values(["session_date", "isin"]).reset_index(drop=True)


def assign_labels(
    forward: pd.DataFrame,
    *,
    horizon: int,
    top_quantile: float,
    bottom_quantile: float,
    selection_policy: SelectionPolicy,
    universe_mode: UniverseMode,
    label_version: str,
    label_source: str,
    pilot_isins: list[str] | None = None,
    sample_weight: float = 1.0,
) -> pd.DataFrame:
    """Assign bullish/bearish/neutral within each session_date."""
    if forward.empty:
        return pd.DataFrame(columns=list(LABEL_COLUMNS))

    allowed = _resolve_universe_isins(forward, universe_mode=universe_mode, pilot_isins=pilot_isins)
    src = forward.loc[forward["isin"].astype(str).isin(allowed)].copy()
    if src.empty:
        return pd.DataFrame(columns=list(LABEL_COLUMNS))

    pieces: list[pd.DataFrame] = []
    for _session, g in src.groupby("session_date", sort=True):
        g = g.copy()
        n = len(g)
        k_top, k_bot = top_bottom_sizes(n, top_quantile, bottom_quantile, selection_policy)

        # Deterministic tie-break (ADR-06):
        #   bullish top-k: sort (R desc, isin asc)
        #   bearish bottom-k: sort (R asc, isin asc)
        # On rare overlap after shrink, bullish wins.
        labels = pd.Series("neutral", index=g.index, dtype=object)
        if k_bot > 0:
            bear_idx = g.sort_values(["forward_return", "isin"], ascending=[True, True]).index[
                :k_bot
            ]
            labels.loc[bear_idx] = "bearish"
        if k_top > 0:
            bull_idx = g.sort_values(["forward_return", "isin"], ascending=[False, True]).index[
                :k_top
            ]
            labels.loc[bull_idx] = "bullish"

        g = g.assign(
            label=labels.to_numpy(),
            horizon=horizon,
            universe_size=n,
            label_version=label_version,
            universe_mode=universe_mode,
            selection_policy=selection_policy,
            top_quantile=float(top_quantile),
            bottom_quantile=float(bottom_quantile),
            sample_weight=float(sample_weight),
            label_source=label_source,
        )
        pieces.append(g)

    out = pd.concat(pieces, ignore_index=True)
    out = out[list(LABEL_COLUMNS)]
    return out.sort_values(["session_date", "isin"]).reset_index(drop=True)


def validate_label_frame(frame: pd.DataFrame, *, horizon: int, label_version: str) -> list[str]:
    """Return validation errors (empty if ok)."""
    errors: list[str] = []
    for col in LABEL_COLUMNS:
        if col not in frame.columns:
            errors.append(f"missing column {col}")
    if errors:
        return errors

    key = ["isin", "session_date", "horizon", "label_version"]
    dup = frame.duplicated(subset=key, keep=False)
    if bool(dup.any()):
        errors.append(
            f"duplicate keys (isin, session_date, horizon, label_version): "
            f"{int(dup.sum())} rows involved"
        )

    if not frame.empty:
        if not (frame["horizon"] == horizon).all():
            errors.append("horizon column mismatch")
        if not (frame["label_version"] == label_version).all():
            errors.append("label_version column mismatch")
        bad_label = ~frame["label"].isin(["bullish", "bearish", "neutral"])
        if bool(bad_label.any()):
            errors.append("invalid label class values")
        rets = pd.to_numeric(frame["forward_return"], errors="coerce")
        if any(not math.isfinite(float(x)) for x in rets):
            errors.append("non-finite forward_return values")

        # Per-session class counts vs k_top/k_bot
        for session, g in frame.groupby("session_date", sort=False):
            n = int(g["universe_size"].iloc[0])
            if not (g["universe_size"] == n).all():
                errors.append(f"{session}: inconsistent universe_size")
            policy = str(g["selection_policy"].iloc[0])
            tq = float(g["top_quantile"].iloc[0])
            bq = float(g["bottom_quantile"].iloc[0])
            k_top, k_bot = top_bottom_sizes(n, tq, bq, policy)  # type: ignore[arg-type]
            n_bull = int((g["label"] == "bullish").sum())
            n_bear = int((g["label"] == "bearish").sum())
            n_neu = int((g["label"] == "neutral").sum())
            if n_bull != k_top or n_bear != k_bot or n_bull + n_bear + n_neu != n:
                errors.append(
                    f"{pd.Timestamp(session).date()}: class counts "
                    f"bull={n_bull}/{k_top} bear={n_bear}/{k_bot} neu={n_neu} n={n}"
                )

    return errors
