"""Dataset registry: names, schemas, unique keys, column contracts."""

from __future__ import annotations

DATASETS = (
    "equity_eod",
    "corporate_actions",
    "symbol_isin_map",
    "trading_calendar",
)

# Required for L0 publish of a successful ingest
REQUIRED_FOR_L0 = frozenset({"equity_eod", "corporate_actions"})

# Required for L1 publish
REQUIRED_FOR_L1 = frozenset({"equity_eod", "corporate_actions", "trading_calendar"})

SCHEMA_VERSIONS: dict[str, str] = {
    "equity_eod": "v1",
    "corporate_actions": "v1",
    "symbol_isin_map": "v1",
    "trading_calendar": "v1",
}

UNIQUE_KEYS: dict[str, tuple[str, ...]] = {
    "equity_eod": ("isin", "session_date"),
    "corporate_actions": ("isin", "ex_date", "action_type"),
    "symbol_isin_map": ("isin", "symbol", "valid_from"),
    "trading_calendar": ("session_date",),
}

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "equity_eod": ("isin", "symbol", "session_date", "close"),
    "corporate_actions": ("isin", "ex_date", "action_type"),
    "symbol_isin_map": ("isin", "symbol"),
    "trading_calendar": ("session_date", "is_open"),
}

OPTIONAL_COLUMNS: dict[str, tuple[str, ...]] = {
    "equity_eod": ("open", "high", "low", "volume", "traded_value"),
    "corporate_actions": ("symbol", "ratio_num", "ratio_den", "factor", "notes"),
    "symbol_isin_map": ("valid_from", "valid_to"),
    "trading_calendar": ("source",),
}

L0_COLUMNS: dict[str, tuple[str, ...]] = {
    "equity_eod": (
        "isin",
        "symbol",
        "session_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "traded_value",
    ),
    "corporate_actions": (
        "isin",
        "symbol",
        "ex_date",
        "action_type",
        "ratio_num",
        "ratio_den",
        "factor",
        "notes",
        "adjusts_price_return",
    ),
    "symbol_isin_map": ("isin", "symbol", "valid_from", "valid_to"),
    "trading_calendar": ("session_date", "is_open", "source"),
}

L1_EQUITY_COLUMNS: tuple[str, ...] = (
    "isin",
    "symbol",
    "session_date",
    "open_raw",
    "high_raw",
    "low_raw",
    "close_raw",
    "volume_raw",
    "traded_value",
    "open_adj",
    "high_adj",
    "low_adj",
    "close_adj",
    "volume_adj",
)

LINEAGE_COLUMNS: tuple[str, ...] = (
    "source_file",
    "raw_sha256",
    "ingested_at",
    "provider",
    "schema_version",
    "dataset_version",
    "run_id",
)

# Action types that participate in V1 price-return adjustment (not dividends)
PRICE_RETURN_ACTION_TYPES = frozenset(
    {
        "split",
        "bonus",
        "consolidation",
        "rights",
        "demerger",
        "spinoff",
        "spin_off",
    }
)

# Backward-compat alias used by older imports
REQUIRED_DATASETS = REQUIRED_FOR_L0
CLEAN_COLUMNS = L0_COLUMNS
