"""Normalize incoming CSV frames into L0 schemas (ISIN-canonical, unadjusted)."""

from __future__ import annotations

import pandas as pd

from stock_engine.ingest.datasets import L0_COLUMNS, PRICE_RETURN_ACTION_TYPES


def normalize_equity_eod(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    out["isin"] = out["isin"].astype(str).str.strip().str.upper()
    out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
    out["session_date"] = pd.to_datetime(out["session_date"], errors="coerce").dt.normalize()
    for col in ("open", "high", "low", "close", "volume", "traded_value"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = pd.NA
    cols = list(L0_COLUMNS["equity_eod"])
    return out[cols].sort_values(["isin", "session_date"]).reset_index(drop=True)


def normalize_corporate_actions(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    out["isin"] = out["isin"].astype(str).str.strip().str.upper()
    if "symbol" not in out.columns:
        out["symbol"] = pd.NA
    else:
        out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
        out.loc[out["symbol"].isin(["NAN", "NONE", "<NA>"]), "symbol"] = pd.NA
    out["ex_date"] = pd.to_datetime(out["ex_date"], errors="coerce").dt.normalize()
    out["action_type"] = out["action_type"].astype(str).str.strip().str.lower()
    for col in ("ratio_num", "ratio_den", "factor"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = pd.NA
    if "notes" not in out.columns:
        out["notes"] = pd.NA
    out["adjusts_price_return"] = out["action_type"].isin(PRICE_RETURN_ACTION_TYPES)
    cols = list(L0_COLUMNS["corporate_actions"])
    return out[cols].sort_values(["isin", "ex_date", "action_type"]).reset_index(drop=True)


def normalize_symbol_isin_map(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    out["isin"] = out["isin"].astype(str).str.strip().str.upper()
    out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
    for col in ("valid_from", "valid_to"):
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.normalize()
        else:
            out[col] = pd.NaT
    # Stable key fill for uniqueness
    out["valid_from"] = out["valid_from"].fillna(pd.Timestamp("0001-01-01"))
    cols = list(L0_COLUMNS["symbol_isin_map"])
    return out[cols].sort_values(["isin", "symbol", "valid_from"]).reset_index(drop=True)


def normalize_trading_calendar(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    out["session_date"] = pd.to_datetime(out["session_date"], errors="coerce").dt.normalize()
    if out["is_open"].dtype == object:
        out["is_open"] = (
            out["is_open"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False})
        )
    out["is_open"] = out["is_open"].astype("boolean")
    if "source" not in out.columns:
        out["source"] = "user_csv"
    else:
        out["source"] = out["source"].astype(str)
    cols = list(L0_COLUMNS["trading_calendar"])
    return out[cols].sort_values(["session_date"]).reset_index(drop=True)
