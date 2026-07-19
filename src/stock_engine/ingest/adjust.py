"""Price-return backward adjustment (V1 — ignores ordinary cash dividends)."""

from __future__ import annotations

import pandas as pd

from stock_engine.ingest.datasets import (
    ADJUSTMENT_METHOD,
    L1_EQUITY_COLUMNS,
    PRICE_RETURN_ACTION_TYPES,
)


def resolve_price_factor(row: pd.Series) -> float | None:
    """
    Resolve a single-event price multiplier for backward adjustment.

    Note: V1 uses float; post-V1 should migrate cumulative products to Decimal
    (or another deterministic numeric type) to avoid long-history drift.
    """
    if pd.notna(row.get("factor")):
        val = float(row["factor"])
        return val if val > 0 else None
    num, den = row.get("ratio_num"), row.get("ratio_den")
    if pd.notna(num) and pd.notna(den) and float(den) != 0:
        val = float(num) / float(den)
        return val if val > 0 else None
    return None


def build_l1_equity_eod(
    equity_l0: pd.DataFrame,
    corporate_actions_l0: pd.DataFrame,
    *,
    outlier_abs_return: float = 0.5,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Backward price-return adjust OHLC; retain raw + adj columns.

    Returns (l1_df, warning_messages).
    """
    warnings: list[str] = []
    eq = equity_l0.copy()
    eq["session_date"] = pd.to_datetime(eq["session_date"]).dt.normalize()

    if len(corporate_actions_l0):
        ca = corporate_actions_l0.copy()
        ca["ex_date"] = pd.to_datetime(ca["ex_date"]).dt.normalize()
        ca = ca[ca["action_type"].isin(PRICE_RETURN_ACTION_TYPES)].copy()
        ca["price_factor"] = ca.apply(resolve_price_factor, axis=1)
        # Rows that claim to adjust but lack factor are excluded here; DQ should
        # have failed closed earlier for missing factors on adjusting types.
        ca = ca[ca["price_factor"].notna()].copy()
    else:
        ca = corporate_actions_l0.iloc[0:0].copy()

    frames: list[pd.DataFrame] = []
    for isin, grp in eq.groupby("isin", sort=True):
        g = grp.sort_values("session_date").copy()
        events = ca[ca["isin"] == isin].sort_values("ex_date") if len(ca) else ca

        adj_factors: list[float] = []
        for sess in g["session_date"]:
            if len(events) == 0:
                adj_factors.append(1.0)
                continue
            mask = events["ex_date"] > sess
            if bool(mask.any()):
                adj_factors.append(float(events.loc[mask, "price_factor"].astype(float).prod()))
            else:
                adj_factors.append(1.0)
        g["cumulative_adjustment_factor"] = adj_factors
        g["adjustment_method"] = ADJUSTMENT_METHOD

        for raw_col in ("open", "high", "low", "close"):
            g[f"{raw_col}_raw"] = pd.to_numeric(g[raw_col], errors="coerce")
            g[f"{raw_col}_adj"] = g[f"{raw_col}_raw"] * g["cumulative_adjustment_factor"]

        g["volume_raw"] = pd.to_numeric(g.get("volume"), errors="coerce")
        g["volume_adj"] = g["volume_raw"] / g["cumulative_adjustment_factor"]
        g["traded_value"] = pd.to_numeric(g.get("traded_value"), errors="coerce")

        g = g.sort_values("session_date")
        rets = g["close_adj"].pct_change().abs()
        event_dates = set(events["ex_date"].tolist()) if len(events) else set()
        for idx, ret in rets.items():
            if pd.isna(ret) or ret <= outlier_abs_return:
                continue
            sess = g.loc[idx, "session_date"]
            if sess not in event_dates:
                warnings.append(
                    f"outlier_return {isin} {pd.Timestamp(sess).date()} abs_ret={ret:.2%} no CA"
                )

        frames.append(g)

    if not frames:
        empty = pd.DataFrame(columns=list(L1_EQUITY_COLUMNS))
        return empty, warnings

    out = pd.concat(frames, ignore_index=True)
    out = out[list(L1_EQUITY_COLUMNS)].sort_values(["isin", "session_date"]).reset_index(drop=True)
    return out, warnings
