"""Data quality gates — fail closed before L0/L1 publish."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from stock_engine.ingest.datasets import REQUIRED_COLUMNS, UNIQUE_KEYS
from stock_engine.ingest.raw_store import sha256_file


@dataclass
class DQIssue:
    code: str
    message: str


@dataclass
class DQReport:
    dataset: str
    ok: bool
    row_count: int
    issues: list[DQIssue] = field(default_factory=list)

    def fail(self, code: str, message: str) -> None:
        self.ok = False
        self.issues.append(DQIssue(code=code, message=message))

    def warn(self, code: str, message: str) -> None:
        self.issues.append(DQIssue(code=f"warn:{code}", message=message))


def verify_checksum(path, expected_sha256: str) -> DQIssue | None:
    actual = sha256_file(path)
    if actual != expected_sha256:
        return DQIssue(
            code="checksum_mismatch",
            message=f"expected {expected_sha256}, got {actual}",
        )
    return None


def validate_unique_keys(df: pd.DataFrame, dataset: str, report: DQReport) -> None:
    keys = UNIQUE_KEYS[dataset]
    missing = [c for c in keys if c not in df.columns]
    if missing:
        report.fail("missing_key_columns", f"Missing key columns: {missing}")
        return
    work = df.copy()
    for k in keys:
        if pd.api.types.is_datetime64_any_dtype(work[k]):
            continue
        # valid_from may be filled already; other keys must not be null
        if k != "valid_from" and work[k].isna().any():
            report.fail("null_key", f"Null values in unique key column {k}")
    dup = work.duplicated(subset=list(keys), keep=False)
    if dup.any():
        report.fail(
            "duplicate_keys",
            f"{int(dup.sum())} rows violate unique key {keys}",
        )


def validate_equity_eod(
    df: pd.DataFrame,
    *,
    prior_row_count: int | None = None,
    row_count_deviation: float = 0.5,
) -> DQReport:
    report = DQReport(dataset="equity_eod", ok=True, row_count=len(df))
    _require_columns(df, "equity_eod", report)
    if not report.ok:
        return report

    if df["isin"].isna().any() or (df["isin"].astype(str).str.len() == 0).any():
        report.fail("missing_isin", "One or more rows missing ISIN")

    if df["close"].isna().any():
        report.fail("missing_close", "One or more rows missing close price")

    if (pd.to_numeric(df["close"], errors="coerce") <= 0).any():
        report.fail("non_positive_close", "Close must be > 0")

    dates = pd.to_datetime(df["session_date"], errors="coerce")
    if dates.isna().any():
        report.fail("invalid_dates", "One or more session_date values are invalid")

    validate_unique_keys(df, "equity_eod", report)

    if "symbol" in df.columns:
        sym_dup = df.duplicated(subset=["symbol", "session_date"], keep=False)
        if sym_dup.any():
            report.fail(
                "duplicate_symbols",
                f"{int(sym_dup.sum())} duplicate symbol+session_date rows",
            )

    _ohlc_structure(df, report)
    _row_count_gate(report, prior_row_count, row_count_deviation)
    return report


def validate_corporate_actions(
    df: pd.DataFrame,
    *,
    prior_row_count: int | None = None,
    row_count_deviation: float = 0.5,
) -> DQReport:
    report = DQReport(dataset="corporate_actions", ok=True, row_count=len(df))
    _require_columns(df, "corporate_actions", report)
    if not report.ok:
        return report

    if df["isin"].isna().any() or (df["isin"].astype(str).str.len() == 0).any():
        report.fail("missing_isin", "One or more rows missing ISIN")

    dates = pd.to_datetime(df["ex_date"], errors="coerce")
    if dates.isna().any():
        report.fail("invalid_dates", "One or more ex_date values are invalid")

    if df["action_type"].isna().any() or (df["action_type"].astype(str).str.len() == 0).any():
        report.fail("missing_action_type", "One or more rows missing action_type")

    validate_unique_keys(df, "corporate_actions", report)

    # Price-return adjusting rows need a resolvable factor
    if "adjusts_price_return" in df.columns:
        adj = df[df["adjusts_price_return"].fillna(False)]
        for _, row in adj.iterrows():
            factor = _resolve_factor(row)
            if factor is None or factor <= 0:
                report.fail(
                    "missing_ca_factor",
                    f"Price-return CA lacks factor: {row.get('isin')} "
                    f"{row.get('ex_date')} {row.get('action_type')}",
                )
                break

    _row_count_gate(report, prior_row_count, row_count_deviation)
    return report


def validate_symbol_isin_map(df: pd.DataFrame) -> DQReport:
    report = DQReport(dataset="symbol_isin_map", ok=True, row_count=len(df))
    _require_columns(df, "symbol_isin_map", report)
    if not report.ok:
        return report
    if df["isin"].isna().any() or df["symbol"].isna().any():
        report.fail("missing_ids", "isin and symbol are required")
    validate_unique_keys(df, "symbol_isin_map", report)
    return report


def validate_trading_calendar(df: pd.DataFrame) -> DQReport:
    report = DQReport(dataset="trading_calendar", ok=True, row_count=len(df))
    _require_columns(df, "trading_calendar", report)
    if not report.ok:
        return report
    dates = pd.to_datetime(df["session_date"], errors="coerce")
    if dates.isna().any():
        report.fail("invalid_dates", "Invalid session_date in calendar")
    if df["is_open"].isna().any():
        report.fail("missing_is_open", "is_open is required")
    validate_unique_keys(df, "trading_calendar", report)
    if not bool(df["is_open"].astype("boolean").fillna(False).any()):
        report.fail("no_open_sessions", "Calendar has no open sessions")
    return report


def parse_as_of_from_equity(df: pd.DataFrame) -> date:
    dates = pd.to_datetime(df["session_date"], errors="coerce")
    if dates.isna().all():
        msg = "Cannot infer as_of_date from equity_eod session_date"
        raise ValueError(msg)
    return dates.max().date()


def _resolve_factor(row: pd.Series) -> float | None:
    if pd.notna(row.get("factor")):
        return float(row["factor"])
    num, den = row.get("ratio_num"), row.get("ratio_den")
    if pd.notna(num) and pd.notna(den) and float(den) != 0:
        return float(num) / float(den)
    return None


def _require_columns(df: pd.DataFrame, dataset: str, report: DQReport) -> None:
    required = REQUIRED_COLUMNS[dataset]
    missing = [c for c in required if c not in df.columns]
    if missing:
        report.fail("missing_columns", f"Missing required columns: {missing}")


def _ohlc_structure(df: pd.DataFrame, report: DQReport) -> None:
    if not {"high", "low", "close"}.issubset(df.columns):
        return
    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")
    close = pd.to_numeric(df["close"], errors="coerce")
    both = high.notna() & low.notna()
    if both.any() and (high[both] < low[both]).any():
        report.fail("ohlc_high_lt_low", "high < low in one or more rows")
    band = high.notna() & low.notna() & close.notna()
    if band.any():
        bad = (close[band] > high[band]) | (close[band] < low[band])
        if bad.any():
            report.fail("ohlc_close_outside", "close outside high/low range")
    if "volume" in df.columns:
        vol = pd.to_numeric(df["volume"], errors="coerce")
        if (vol.notna() & (vol < 0)).any():
            report.fail("negative_volume", "volume < 0")


def _row_count_gate(
    report: DQReport,
    prior_row_count: int | None,
    deviation: float,
) -> None:
    if prior_row_count is None or prior_row_count <= 0:
        return
    lower = prior_row_count * (1.0 - deviation)
    upper = prior_row_count * (1.0 + deviation)
    if report.row_count < lower or report.row_count > upper:
        report.fail(
            "row_count_deviation",
            f"row_count={report.row_count} outside "
            f"[{lower:.0f}, {upper:.0f}] vs prior={prior_row_count}",
        )
