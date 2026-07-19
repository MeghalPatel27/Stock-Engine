"""Normalize incoming CSV frames into internal clean schemas (ISIN-canonical)."""

from __future__ import annotations

import pandas as pd

from stock_engine.ingest.datasets import CLEAN_COLUMNS


def normalize_equity_eod(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    out["isin"] = out["isin"].astype(str).str.strip().str.upper()
    out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
    out["session_date"] = pd.to_datetime(out["session_date"], errors="coerce").dt.date
    for col in ("open", "high", "low", "close", "volume", "traded_value", "adj_close"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = pd.NA
    return out[list(CLEAN_COLUMNS["equity_eod"])]


def normalize_corporate_actions(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    out["isin"] = out["isin"].astype(str).str.strip().str.upper()
    if "symbol" not in out.columns:
        out["symbol"] = pd.NA
    else:
        out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
    out["ex_date"] = pd.to_datetime(out["ex_date"], errors="coerce").dt.date
    out["action_type"] = out["action_type"].astype(str).str.strip().str.lower()
    for col in ("ratio_num", "ratio_den", "factor"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = pd.NA
    if "notes" not in out.columns:
        out["notes"] = pd.NA
    return out[list(CLEAN_COLUMNS["corporate_actions"])]


def normalize_symbol_isin_map(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    out["isin"] = out["isin"].astype(str).str.strip().str.upper()
    out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
    for col in ("valid_from", "valid_to"):
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.date
        else:
            out[col] = pd.NA
    return out[list(CLEAN_COLUMNS["symbol_isin_map"])]
