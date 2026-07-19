"""Dataset names and required CSV columns for V1 local inputs."""

from __future__ import annotations

DATASETS = (
    "equity_eod",
    "corporate_actions",
    "symbol_isin_map",
)

# Mandatory datasets for a successful ingest run
REQUIRED_DATASETS = frozenset({"equity_eod", "corporate_actions"})

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "equity_eod": ("isin", "symbol", "session_date", "close"),
    "corporate_actions": ("isin", "ex_date", "action_type"),
    "symbol_isin_map": ("isin", "symbol"),
}

OPTIONAL_COLUMNS: dict[str, tuple[str, ...]] = {
    "equity_eod": ("open", "high", "low", "volume", "traded_value", "adj_close"),
    "corporate_actions": ("symbol", "ratio_num", "ratio_den", "factor", "notes"),
    "symbol_isin_map": ("valid_from", "valid_to"),
}

CLEAN_COLUMNS: dict[str, tuple[str, ...]] = {
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
        "adj_close",
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
    ),
    "symbol_isin_map": ("isin", "symbol", "valid_from", "valid_to"),
}
