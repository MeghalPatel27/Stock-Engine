# Data Requirements vs Public Indian Market Availability

**Date:** 2026-07-19  
**Purpose:** Align engine foundations with data that is actually obtainable. Prevent building on unavailable fields.  
**V1 mode:** User/manual CSV into `data/incoming/` (no live downloaders in code yet).

---

## 1. What the engine needs (priority order)

### A. Mandatory for current pipeline (L0 → L1)

| # | Dataset | Why | Minimum history |
|---|---|---|---|
| 1 | **equity_eod** | OHLCV + traded value; returns, ADV, liquidity | ≥ **5 years** daily |
| 2 | **corporate_actions** | Price-return adjustment (split/bonus/…); mandatory | Same span as prices |
| 3 | **trading_calendar** | Canonical sessions; missing-day checks; T+N horizons | Same span |
| 4 | **symbol ↔ ISIN map** | Canonical id = ISIN; symbol is display | Current + history of renames if possible |

### B. Mandatory before universe / ranking (Phase 1 rules)

| # | Dataset | Why |
|---|---|---|
| 5 | **F&O underlying membership (as-of)** | Universe = F&O equities ∩ liquidity |
| 6 | **Security master / listing date** | IPO &lt; 6 months exclusion |
| 7 | **F&O ban list (daily)** | Hard exclusion |
| 8 | **ASM / GSM lists** | Hard exclusion |
| 9 | **Halt / not-traded flags** (or infer carefully) | Exclusion / bad labels |

### C. Strongly useful soon (not blocking L1 clean)

| # | Dataset | Why |
|---|---|---|
| 10 | **Delivery %** | Feature / risk (not membership) |
| 11 | **Earnings / results calendar** | Event risk (deferred OK) |
| 12 | **Index EOD (Nifty 50 / sector)** | Regime features later (not for labels) |

### D. Later enrichment (explicitly deferred)

F&O derivatives OI / PCR / rollover, fundamentals, shareholding, news/sentiment.

---

## 2. Columns we expect you to prepare (V1 CSV contracts)

See also [`incoming.md`](incoming.md) and [`dictionary/`](dictionary/).

### equity_eod.csv
`isin, symbol, session_date, open, high, low, close, volume, traded_value`  
(close required; others strongly preferred)

### corporate_actions.csv
`isin, ex_date, action_type, ratio_num, ratio_den, factor, symbol, notes`  
For split/bonus/etc.: **factor or ratios required**. Ordinary dividends OK without price factor.

### trading_calendar.csv
`session_date, is_open` (+ optional `source`)

### symbol_isin_map.csv
`isin, symbol, valid_from, valid_to`

### (Next to add when we extend ingest)
- `fno_universe.csv` — `isin, symbol, as_of_date, in_fno`
- `exclusions.csv` — `isin, session_date, reason` (`ban`/`asm`/`gsm`/`halt`/`merger`/…)
- `security_master.csv` — `isin, listing_date, status, successor_isin`

---

## 3. What is publicly available in India (as of mid‑2026)

> Official sources change formats/URLs. Treat this as a **capability map**, not frozen endpoints. Always prefer NSE/BSE official over Yahoo-style globals for India CA/PIT.

### ✅ Strong public / official coverage

| Need | Public source (typical) | Notes |
|---|---|---|
| Daily equity EOD (OHLC, volume) | **NSE CM-UDiFF Common Bhavcopy** (replaced old bhavcopy Jul 2024) | Via [NSE All Reports](https://www.nseindia.com/all-reports); archives under `nsearchives.nseindia.com` |
| Delivery data | NSE “Full Bhavcopy / deliverable” style reports | Useful for delivery % later |
| F&O daily derivatives EOD | **NSE FO UDiFF bhavcopy** | Later phase (OI etc.) |
| Equity master + **ISIN** + listing date | `EQUITY_L.csv` (NSE equities content) | Good for security master / symbol↔ISIN |
| F&O equity list (current) | NSE F&O equity list / lot size files | **Point-in-time history** of membership is the hard part |
| F&O ban | Daily `fo_secban_*.csv` (NSE Clearing / archives) | Available daily; need to archive yourself for history |
| ASM | [NSE ASM reports](https://www.nseindia.com/reports/asm) (CSV download; includes ISIN) | Snapshot pages; archive daily for PIT |
| GSM | NSE GSM reports (similar) | Same archival discipline |
| Holidays | [NSE holidays page](https://www.nseindia.com/resources/exchange-communication-holidays); Nifty Indices holiday CSV | Build full open-day calendar = all weekdays − holidays − weekends (+ Muhurat exceptions) |
| Corporate actions | NSE corporate actions / filings APIs & reports; also BSE | Free but **messy**; quality varies; need cleaning into our CA schema |
| Indices EOD | NSE index reports / Nifty Indices | Optional for V1 labels |

### ⚠️ Available but painful / incomplete

| Need | Reality |
|---|---|
| **5+ years CA with clean factors** | Not one perfect free file. Must assemble from NSE/BSE CA feeds + validate factors against price jumps |
| **Historical F&O membership** | Current list is easy; reconstructing “was X in F&O on date T?” needs archived lists/circulars |
| **Historical ASM/GSM/ban** | Official today; **you must save daily** — free archives of multi-year history are incomplete unless you collect |
| **Adjusted prices from exchange** | Exchange gives **raw** bhavcopy; **adjustment is our job** (ADR-04) — do not trust Yahoo adj for India as primary |
| **Halt history** | Partial; often inferred from missing prints / exchange messages |

### ❌ Weak / avoid as foundation

| Source | Why avoid as system of record |
|---|---|
| Yahoo Finance / generic global APIs | Weak India CA, symbol quirks, ToS/reliability |
| Random scraped sites | Breakage + legal/ToS risk |
| Paid vendors | OK later inside ₹2–5k if free path fails completeness — not assumed |

### Community helpers (not “official”, optional later)

Libraries such as `nselib`, `jugaad-data`, `indian-market-data` wrap NSE archives/APIs. Useful for **your offline prep scripts**, but V1 engine stays CSV-in; do not couple `src/` to them until a future provider adapter is approved.

---

## 4. Recommended data prep plan (so we don’t build wrong)

### Phase P (now — before more engine features)

Prepare and keep local (your machine → drop into `data/incoming/`):

1. **5 years equity_eod** for ~all current F&O names (raw OHLC from UDiFF bhavcopy), keyed by **ISIN**  
2. **Corporate actions** for those ISINs (splits/bonuses with factors; dividends stored)  
3. **trading_calendar** open days for that span  
4. **symbol_isin_map** from `EQUITY_L` (+ manual rename fixes)  

### Phase Q (before ranking/universe automation)

5. Daily archive of **F&O list**, **ban**, **ASM/GSM** (even if engine only uses recent at first)  
6. `security_master` with listing dates from `EQUITY_L`  

### Phase R (enrichment)

7. Delivery %  
8. Earnings calendar  
9. Derivatives OI (optional)

---

## 5. Honest gaps to design around

| Gap | Engine implication |
|---|---|
| No free perfect multi-year ban/ASM history | Backtests of exclusions will be incomplete unless you archive going forward; historical paper may use “exclusions from date D onward” |
| CA factors often missing/wrong in public feeds | DQ fail-closed on missing factors (already); human fix CA CSV |
| Symbol changes / mergers | ISIN + map + merger exclusion windows (Phase 1/3) — don’t stitch blindly |
| UDiFF vs old bhavcopy format break (2024) | Any downloader must support **UDiFF**; old tutorials are stale |

---

## 6. What you should collect first (checklist)

- [ ] NSE UDiFF equity bhavcopy → map to `equity_eod.csv` with **ISIN**  
- [ ] Corporate actions → `corporate_actions.csv` with factors for splits/bonuses  
- [ ] Build `trading_calendar.csv` from NSE holidays + weekdays  
- [ ] `EQUITY_L.csv` → `symbol_isin_map.csv` + listing dates  
- [ ] Current F&O list (snapshot)  
- [ ] Start **daily saving** ban + ASM/GSM CSVs from today (future PIT)

---

## 7. What we will *not* assume

- That Yahoo adjusted close is correct  
- That F&O universe was stable historically without archives  
- That dividends must adjust price-return L1 (they don’t in V1)  
- That we can scrape NSE inside the engine in V1 (manual CSV first)

When your CSVs match §2, the existing ingest/L1 path can run without guessing.
