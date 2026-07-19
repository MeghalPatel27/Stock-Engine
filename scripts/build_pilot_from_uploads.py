#!/usr/bin/env python3
"""
Convert NSE Quote / Corporate Action / holiday inputs into engine CSVs.

Usage (from repo root):
  uv run python scripts/build_pilot_from_uploads.py
"""

from __future__ import annotations

import re
from datetime import date, datetime
from io import StringIO
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
UPLOADS = Path("/home/ubuntu/.cursor/projects/workspace/uploads")
OUT = ROOT / "data" / "incoming"
PREPARED = ROOT / "docs" / "data" / "pilot_5_stocks" / "prepared"

ISIN = {
    "RELIANCE": "INE002A01018",
    "TCS": "INE467B01029",
    "INFY": "INE009A01021",
    "HDFCBANK": "INE040A01034",
    "ICICIBANK": "INE090A01021",
}

HOLIDAYS_2026 = [
    "2026-01-15",
    "2026-01-26",
    "2026-03-03",
    "2026-03-26",
    "2026-03-31",
    "2026-04-03",
    "2026-04-14",
    "2026-05-01",
    "2026-05-28",
    "2026-06-26",
    "2026-09-14",
    "2026-10-02",
    "2026-10-20",
    "2026-11-10",
    "2026-11-24",
    "2026-12-25",
]


def _num(x) -> float:
    if pd.isna(x):
        return float("nan")
    s = str(x).strip().replace(",", "").replace('"', "")
    if s in {"", "-", "nan"}:
        return float("nan")
    return float(s)


def load_symbol_quotes(symbol: str) -> pd.DataFrame:
    files = sorted(UPLOADS.glob(f"Quote-Equity-{symbol}-EQ-*.csv"))
    if not files:
        raise FileNotFoundError(f"No Quote-Equity files for {symbol} in uploads/")
    frames: list[pd.DataFrame] = []
    for path in files:
        df = pd.read_csv(path)
        df.columns = [c.strip() for c in df.columns]
        rows = []
        for _, r in df.iterrows():
            sess = datetime.strptime(str(r["DATE"]).strip(), "%d-%b-%Y").date()
            rows.append(
                {
                    "isin": ISIN[symbol],
                    "symbol": symbol,
                    "session_date": sess.isoformat(),
                    "open": _num(r["OPEN"]),
                    "high": _num(r["HIGH"]),
                    "low": _num(r["LOW"]),
                    "close": _num(r["CLOSE"]),
                    "volume": _num(r["VOLUME"]),
                    "traded_value": _num(r["VALUE"]),
                }
            )
        frames.append(pd.DataFrame(rows))
    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["isin", "session_date"], keep="last")
    return out.sort_values("session_date").reset_index(drop=True)


def load_all_quotes() -> pd.DataFrame:
    frames = [load_symbol_quotes(sym) for sym in ISIN]
    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["isin", "session_date"], keep="last")
    return out.sort_values(["session_date", "symbol"]).reset_index(drop=True)


def parse_purpose(purpose: str) -> tuple[str, float | None, float | None, float | None, str]:
    """Return action_type, ratio_num, ratio_den, factor, notes."""
    p = purpose.strip()
    pl = p.lower()

    m = re.search(r"bonus\s+(\d+)\s*:\s*(\d+)", pl)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        factor = b / (a + b)
        return "bonus", float(b), float(a + b), factor, p

    m = re.search(r"split\s+(\d+)\s*:\s*(\d+)", pl)
    if m:
        n1, n2 = int(m.group(1)), int(m.group(2))
        factor = n1 / n2 if n2 else None
        return "split", float(n1), float(n2), factor, p

    if "buy back" in pl or "buyback" in pl:
        return "buyback", None, None, None, p

    if "dividend" in pl:
        return "dividend", None, None, None, p

    return "other", None, None, None, p


def load_corporate_actions() -> pd.DataFrame:
    files = sorted(UPLOADS.glob("CF-CA-equities-*.csv"))
    rows = []
    for path in files:
        text = path.read_text(encoding="utf-8-sig")
        chunks = re.split(r'(?="SYMBOL","COMPANY NAME")', text)
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk or "SYMBOL" not in chunk[:80]:
                continue
            df = pd.read_csv(StringIO(chunk))
            df.columns = [c.strip().replace('"', "") for c in df.columns]
            for _, r in df.iterrows():
                sym = str(r["SYMBOL"]).strip().upper()
                if sym not in ISIN:
                    continue
                purpose = str(r["PURPOSE"]).strip()
                ex = str(r["EX-DATE"]).strip()
                if ex in {"-", "nan", ""}:
                    continue
                ex_date = datetime.strptime(ex, "%d-%b-%Y").date().isoformat()
                action, rn, rd, factor, notes = parse_purpose(purpose)
                rows.append(
                    {
                        "isin": ISIN[sym],
                        "symbol": sym,
                        "ex_date": ex_date,
                        "action_type": action,
                        "ratio_num": rn if rn is not None else "",
                        "ratio_den": rd if rd is not None else "",
                        "factor": factor if factor is not None else "",
                        "notes": notes,
                    }
                )
    out = pd.DataFrame(rows)
    if len(out) == 0:
        raise RuntimeError("No corporate actions parsed")
    out = out.drop_duplicates(subset=["isin", "ex_date", "action_type"], keep="first")
    return out.sort_values(["isin", "ex_date"]).reset_index(drop=True)


def build_calendar(equity: pd.DataFrame) -> pd.DataFrame:
    """
    Open sessions = union of dates present across pilot equities.
    Also stamp known 2026 holidays as closed.
    """
    open_dates = sorted({date.fromisoformat(d) for d in equity["session_date"]})
    rows = [
        {
            "session_date": d.isoformat(),
            "is_open": "true",
            "source": "derived_from_pilot_quotes",
        }
        for d in open_dates
    ]
    open_set = {d.isoformat() for d in open_dates}
    for h in HOLIDAYS_2026:
        if h not in open_set:
            rows.append(
                {
                    "session_date": h,
                    "is_open": "false",
                    "source": "nse_holidays_2026_user",
                }
            )
    return pd.DataFrame(rows).sort_values("session_date").reset_index(drop=True)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    PREPARED.mkdir(parents=True, exist_ok=True)

    equity = load_all_quotes()
    ca = load_corporate_actions()
    cal = build_calendar(equity)

    equity_path = OUT / "equity_eod.csv"
    ca_path = OUT / "corporate_actions.csv"
    cal_path = OUT / "trading_calendar.csv"
    map_path = OUT / "symbol_isin_map.csv"

    equity.to_csv(equity_path, index=False)
    ca.to_csv(ca_path, index=False)
    cal.to_csv(cal_path, index=False)

    pd.DataFrame(
        [
            {"isin": v, "symbol": k, "valid_from": "2019-01-01", "valid_to": ""}
            for k, v in ISIN.items()
        ]
    ).to_csv(map_path, index=False)

    for src in (equity_path, ca_path, cal_path, map_path):
        (PREPARED / src.name).write_bytes(src.read_bytes())

    counts = equity.groupby("symbol").size().to_dict()
    print(f"equity_eod rows={len(equity)} range={equity.session_date.min()}→{equity.session_date.max()}")
    print(f"per_symbol={counts}")
    print(f"corporate_actions rows={len(ca)}")
    open_n = int((cal["is_open"].astype(str).str.lower() == "true").sum())
    print(f"trading_calendar open={open_n} closed={len(cal) - open_n}")
    print(f"wrote {OUT} and {PREPARED}")
    print("skipped: security_master, fno_membership, exclusions, delivery_eod")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
