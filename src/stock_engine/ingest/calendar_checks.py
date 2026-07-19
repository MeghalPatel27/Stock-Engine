"""Canonical trading calendar helpers and missing-session detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from stock_engine.ingest.validate import DQIssue


@dataclass
class MissingSessionReport:
    ok: bool
    hard_gaps: list[DQIssue] = field(default_factory=list)
    soft_gaps: list[DQIssue] = field(default_factory=list)


def open_sessions(calendar: pd.DataFrame) -> list[date]:
    cal = calendar.copy()
    cal["session_date"] = pd.to_datetime(cal["session_date"]).dt.normalize()
    open_mask = cal["is_open"].astype("boolean").fillna(False)
    dates = cal.loc[open_mask, "session_date"].sort_values().dt.date.tolist()
    return list(dates)


def detect_missing_sessions(
    equity: pd.DataFrame,
    calendar: pd.DataFrame,
    *,
    as_of_date: date,
    lookback_n: int = 5,
) -> MissingSessionReport:
    """
    Hard-fail if an ISIN with prior history misses any of the last N open
    sessions ending at as_of_date.
    Older gaps are soft-warned.
    """
    report = MissingSessionReport(ok=True)
    sessions = open_sessions(calendar)
    if not sessions:
        report.ok = False
        report.hard_gaps.append(DQIssue("no_calendar", "No open sessions in calendar"))
        return report

    sessions = [d for d in sessions if d <= as_of_date]
    if not sessions:
        report.ok = False
        report.hard_gaps.append(
            DQIssue("calendar_after_asof", "No calendar sessions on/before as_of_date")
        )
        return report

    recent = sessions[-lookback_n:] if lookback_n > 0 else []
    recent_set = set(recent)
    older = set(sessions) - recent_set

    eq = equity.copy()
    eq["session_date"] = pd.to_datetime(eq["session_date"]).dt.normalize()
    eq["session_date"] = eq["session_date"].dt.date

    for isin, grp in eq.groupby("isin"):
        observed = set(grp["session_date"].tolist())
        if not observed:
            continue
        first_seen = min(observed)
        # Hard gaps among recent sessions after the name first appears
        hard_missing = sorted(
            d for d in recent_set if d >= first_seen and d not in observed and d <= as_of_date
        )
        if hard_missing:
            report.ok = False
            report.hard_gaps.append(
                DQIssue(
                    "missing_recent_sessions",
                    f"{isin} missing recent sessions: {hard_missing}",
                )
            )
        soft_missing = sorted(
            d for d in older if d >= first_seen and d not in observed and d <= as_of_date
        )
        if soft_missing:
            report.soft_gaps.append(
                DQIssue(
                    "missing_older_sessions",
                    f"{isin} missing older sessions (n={len(soft_missing)}): {soft_missing[:5]}...",
                )
            )
    return report
