# Pilot: 5 stocks — CSV files to build

**Goal:** Gather everything needed for the full product path, starting with **5 liquid F&O names**, using **free public NSE data**, prepared as CSVs for `data/incoming/`.

This environment cannot download NSE files (blocked 403). You download in a browser / on your laptop, then fill the templates in [`templates/`](templates/).

---

## 1. The 5 pilot stocks

| # | Symbol | ISIN | Why |
|---|---|---|---|
| 1 | RELIANCE | `INE002A01018` | Large-cap F&O, liquid |
| 2 | TCS | `INE467B01029` | Large-cap F&O |
| 3 | INFY | `INE009A01021` | Large-cap F&O |
| 4 | HDFCBANK | `INE040A01034` | Large-cap F&O |
| 5 | ICICIBANK | `INE090A01021` | Large-cap F&O |

Confirm ISINs once from NSE `EQUITY_L.csv` (symbols can change; ISIN is canonical).

**History target:** daily from **~2019-01-01 → today** (≥5 years where listed).

---

## 2. CSV files you must build (full product foundation)

Build these files (headers already in `templates/`):

| File | Required for | Scope |
|---|---|---|
| `equity_eod.csv` | L0/L1 prices | All sessions × 5 stocks |
| `corporate_actions.csv` | L1 adjustment + events | All CA for 5 ISINs |
| `trading_calendar.csv` | Sessions / missing days | Full date range |
| `symbol_isin_map.csv` | Identity | 5 rows (+ renames if any) |
| `security_master.csv` | IPO / listing rules | 5 rows |
| `fno_membership.csv` | Universe | Daily or weekly snapshots for 5 (or “in F&O” flags) |
| `exclusions.csv` | Ban/ASM/GSM/halt/merger | Rows when any of 5 is excluded |
| `delivery_eod.csv` | Later feature/risk | Optional now; same dates as equity |
| `earnings_calendar.csv` | Later event risk | Optional now |

For **first successful ingest/L1 today**, minimum is:

1. `equity_eod.csv`  
2. `corporate_actions.csv`  
3. `trading_calendar.csv`  
(+ `symbol_isin_map.csv` recommended)

---

## 3. Column specs + where to pick data (free / public)

### 3.1 `equity_eod.csv` — **start here**

| Column | Required | Source |
|---|---|---|
| `isin` | Yes | Map from symbol via `EQUITY_L.csv` |
| `symbol` | Yes | NSE trading symbol |
| `session_date` | Yes | Trade date `YYYY-MM-DD` |
| `open` | Preferred | NSE **CM-UDiFF Common Bhavcopy** |
| `high` | Preferred | same |
| `low` | Preferred | same |
| `close` | **Yes** | same |
| `volume` | Preferred | same (total traded qty) |
| `traded_value` | Preferred | same (turnover / value) |

**Where (public, free):**

1. Open [NSE All Reports – Equities](https://www.nseindia.com/all-reports)  
2. Download **CM-UDiFF Common Bhavcopy Final (zip)** for each trading day  
   - Archives pattern (may change):  
     `https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip`  
3. Filter rows where ISIN/symbol ∈ pilot 5 and series is equity (typically `EQ`)  
4. Map UDiFF columns → our schema (names vary slightly by file version; common fields include trade date, TckrSymb / Symbol, ISIN, OHLC, TtlTradgVol, TtlTrfVal / similar)

**Do not use Yahoo as the system of record** for this foundation.

**Tip:** For 5 stocks × 5 years ≈ ~1,250 sessions × 5 ≈ 6,250 rows — manageable in Excel/Python on your laptop.

---

### 3.2 `corporate_actions.csv`

| Column | Required | Source |
|---|---|---|
| `isin` | Yes | From CA / EQUITY_L |
| `symbol` | Optional | NSE symbol at time of CA |
| `ex_date` | Yes | Ex-date |
| `action_type` | Yes | `split` / `bonus` / `dividend` / `rights` / `merger` / `demerger` / … (lowercase) |
| `ratio_num` | If no `factor` | e.g. split 1:2 → num=1 den=2 |
| `ratio_den` | If no `factor` | |
| `factor` | For price-return CA | Price multiplier for backward adj (e.g. 2:1 split → `0.5`) |
| `notes` | Optional | Free text |

**Where (public, free):**

- NSE website → **Corporate Actions / Corporate Filings** for each symbol  
- Or NSE “corporate actions” reports/APIs (browser session often required)  
- Cross-check splits/bonuses against price jumps on ex-date  

**Rules for our engine:**

- `split` / `bonus` / `consolidation` / `rights` / `demerger` → need `factor` or ratios  
- `dividend` → store for later total-return; **does not** adjust V1 price-return L1  
- `merger` → store; price not auto-stitched; exclusion window later  

---

### 3.3 `trading_calendar.csv`

| Column | Required | Source |
|---|---|---|
| `session_date` | Yes | Every calendar day in range **or** only open days with `is_open=true` |
| `is_open` | Yes | `true` / `false` |
| `source` | Optional | e.g. `nse_holidays_2026` |

**Where (public, free):**

1. [NSE Market Holidays](https://www.nseindia.com/resources/exchange-communication-holidays)  
2. Optional CSV: [Nifty Indices holiday calendar](https://www.niftyindices.com/resources/holiday-calendar)  
3. Build: all Mon–Fri in range, set `is_open=false` on holidays (and note Muhurat exceptions if you include them)

Simplest V1: **one row per open trading day** with `is_open=true` only (engine open-session list).

---

### 3.4 `symbol_isin_map.csv`

| Column | Required | Source |
|---|---|---|
| `isin` | Yes | `EQUITY_L.csv` → `ISIN NUMBER` |
| `symbol` | Yes | `SYMBOL` |
| `valid_from` | Optional | listing date or `2019-01-01` |
| `valid_to` | Optional | blank if current |

**Where:**  
Download (in browser):  
`https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv`  
(from NSE site / archives — often needs browser cookies)

Filter the 5 symbols; copy ISIN + listing date.

---

### 3.5 `security_master.csv` (for full product / IPO rules)

| Column | Required | Source |
|---|---|---|
| `isin` | Yes | EQUITY_L |
| `symbol` | Yes | EQUITY_L |
| `listing_date` | Yes | EQUITY_L `DATE OF LISTING` |
| `status` | Yes | `active` |
| `successor_isin` | Optional | for mergers later |

---

### 3.6 `fno_membership.csv` (universe)

| Column | Required | Source |
|---|---|---|
| `isin` | Yes | Map from F&O list symbol |
| `symbol` | Yes | F&O underlying symbol |
| `as_of_date` | Yes | Date of the list snapshot |
| `in_fno` | Yes | `true` / `false` |

**Where:** NSE F&O → equity derivatives list / lot-size list (current underlyings).  

For pilot: if all 5 are continuously in F&O (they are), you can start with **one row per stock** with `as_of_date=today`, `in_fno=true`, then add weekly snapshots going forward.

---

### 3.7 `exclusions.csv` (ban / ASM / GSM / halt / merger)

| Column | Required | Source |
|---|---|---|
| `isin` | Yes | |
| `symbol` | Optional | |
| `session_date` | Yes | Day exclusion applies |
| `reason` | Yes | `ban` / `asm` / `gsm` / `halt` / `merger` / `major_ca` |
| `notes` | Optional | |

**Where (public, free):**

| Reason | Source |
|---|---|
| `ban` | Daily NSE F&O ban file `fo_secban_DDMMYYYY.csv` ([NSE archives / clearing](https://www.nseindia.com/all-reports)) |
| `asm` | [NSE ASM reports](https://www.nseindia.com/reports/asm) (CSV includes ISIN) |
| `gsm` | NSE GSM reports |
| `halt` | Exchange halt messages / infer missing session later |
| `merger` | From CA / announcements |

**Pilot tip:** These 5 names are rarely on ASM/GSM. File may be **empty** (header only) for long stretches — that is valid. Start **saving ban/ASM daily from today** for PIT history.

---

### 3.8 Optional now

**`delivery_eod.csv`:** `isin,symbol,session_date,delivery_qty,delivery_pct`  
→ NSE full bhavcopy / deliverable quantity reports.

**`earnings_calendar.csv`:** `isin,symbol,results_date,period`  
→ NSE corporate filings / results calendar (deferred OK).

---

## 4. Suggested build order (your laptop)

```text
1. Download EQUITY_L.csv          → fill symbol_isin_map + security_master
2. Build trading_calendar         → from NSE holidays
3. Download UDiFF bhavcopies      → filter 5 ISINs → equity_eod.csv
4. Collect CA for 5 symbols       → corporate_actions.csv (factors!)
5. Snapshot F&O list              → fno_membership.csv
6. Check ban/ASM for sample days  → exclusions.csv (may be empty)
7. Copy CSVs into data/incoming/
8. Run: uv run stock-engine-ingest --as-of <last_date>
```

---

## 5. Templates

Empty header files (and tiny examples) live in:

`docs/data/pilot_5_stocks/templates/`

Copy them to `data/incoming/` when filled:

```bash
cp docs/data/pilot_5_stocks/templates/*.csv data/incoming/
# then replace with your real filled files
uv run stock-engine-ingest --as-of YYYY-MM-DD
```

---

## 6. Definition of “pilot done”

- [ ] ≥5 years (or max available) `equity_eod` for all 5 ISINs  
- [ ] All splits/bonuses in range have `factor` or ratios  
- [ ] Calendar covers the same range  
- [ ] Ingest status=`success` and `data/clean/l1/equity_eod/` Parquet exists  
- [ ] Spot-check: a known split (if any) shows continuous `close_adj`  

After that we extend the same schemas to the full F&O universe — **without changing the engine contracts**.
