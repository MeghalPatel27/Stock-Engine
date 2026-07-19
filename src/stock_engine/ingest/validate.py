"""Data quality gates — fail closed before clean publish."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from stock_engine.ingest.datasets import REQUIRED_COLUMNS
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


def verify_checksum(path, expected_sha256: str) -> DQIssue | None:
    actual = sha256_file(path)
    if actual != expected_sha256:
        return DQIssue(
            code="checksum_mismatch",
            message=f"expected {expected_sha256}, got {actual}",
        )
    return None


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

    dates = pd.to_datetime(df["session_date"], errors="coerce")
    if dates.isna().any():
        report.fail("invalid_dates", "One or more session_date values are invalid")

    dup_mask = df.duplicated(subset=["isin", "session_date"], keep=False)
    if dup_mask.any():
        n = int(dup_mask.sum())
        report.fail("duplicate_keys", f"{n} duplicate isin+session_date rows")

    # Also flag duplicate symbol+date as soft identity issues when present
    if "symbol" in df.columns:
        sym_dup = df.duplicated(subset=["symbol", "session_date"], keep=False)
        if sym_dup.any():
            report.fail(
                "duplicate_symbols",
                f"{int(sym_dup.sum())} duplicate symbol+session_date rows",
            )

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

    dup = df.duplicated(
        subset=["isin", "ex_date", "action_type"],
        keep=False,
    )
    if dup.any():
        report.fail("duplicate_keys", f"{int(dup.sum())} duplicate CA rows")

    _row_count_gate(report, prior_row_count, row_count_deviation)
    return report


def validate_symbol_isin_map(df: pd.DataFrame) -> DQReport:
    report = DQReport(dataset="symbol_isin_map", ok=True, row_count=len(df))
    _require_columns(df, "symbol_isin_map", report)
    if not report.ok:
        return report
    if df["isin"].isna().any() or df["symbol"].isna().any():
        report.fail("missing_ids", "isin and symbol are required")
    dup = df.duplicated(subset=["isin", "symbol"], keep=False)
    if dup.any():
        report.fail("duplicate_keys", f"{int(dup.sum())} duplicate isin+symbol rows")
    return report


def _require_columns(df: pd.DataFrame, dataset: str, report: DQReport) -> None:
    required = REQUIRED_COLUMNS[dataset]
    missing = [c for c in required if c not in df.columns]
    if missing:
        report.fail("missing_columns", f"Missing required columns: {missing}")


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


def parse_as_of_from_equity(df: pd.DataFrame) -> date:
    dates = pd.to_datetime(df["session_date"], errors="coerce")
    if dates.isna().all():
        msg = "Cannot infer as_of_date from equity_eod session_date"
        raise ValueError(msg)
    return dates.max().date()
