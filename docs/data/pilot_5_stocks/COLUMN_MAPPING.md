# UDiFF / EQUITY_L → our CSV (cheat sheet)

Fill this after you open one real UDiFF file — column names differ slightly by version.

## EQUITY_L.csv → identity files

| EQUITY_L column (typical) | Our column | File |
|---|---|---|
| ISIN NUMBER | `isin` | symbol_isin_map, security_master, equity_eod |
| SYMBOL | `symbol` | same |
| DATE OF LISTING | `listing_date` / `valid_from` | security_master / symbol_isin_map |
| NAME OF COMPANY | (reference only) | — |

## CM-UDiFF bhavcopy → equity_eod

| UDiFF-like field (examples) | Our column |
|---|---|
| ISIN / FinInstrmId | `isin` |
| TckrSymb / Symbol | `symbol` |
| TradDt / Src / business date | `session_date` |
| OpnPric | `open` |
| HghPric | `high` |
| LwPric | `low` |
| ClsPric / LastPric | `close` (prefer official close) |
| TtlTradgVol / TotTrdQty | `volume` |
| TtlTrfVal / TotTrdVal | `traded_value` |
| SctySrs | filter `EQ` (or equivalent equity series) |

Only keep the 5 pilot ISINs.

## Corporate actions

Normalize free-text NSE descriptions into:

| NSE wording (examples) | `action_type` | `factor` hint |
|---|---|---|
| Split / subdivision 1:2 | `split` | 0.5 |
| Bonus 1:1 | `bonus` | 0.5 (2 shares from 1) |
| Dividend | `dividend` | leave blank / ignore for L1 price-return |
| Rights | `rights` | only if you can compute factor |
| Merger / amalgamation | `merger` | no price stitch |

Always verify factor against the price drop/rise on ex-date.
