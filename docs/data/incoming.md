# Local CSV inputs (`data/incoming/`)

## Required files (for successful L1 publish)

| Dataset | Filenames |
|---|---|
| Equity EOD | `equity_eod.csv` or `equity_eod__YYYY-MM-DD.csv` |
| Corporate actions | `corporate_actions.csv` or dated |
| Trading calendar | `trading_calendar.csv` or dated |

## Optional

| Dataset | Filenames |
|---|---|
| Symbol ↔ ISIN map | `symbol_isin_map.csv` or dated |

## Columns

### equity_eod
Required: `isin,symbol,session_date,close`  
Optional: `open,high,low,volume,traded_value`

### corporate_actions
Required: `isin,ex_date,action_type`  
Optional: `symbol,ratio_num,ratio_den,factor,notes`  
Price-return adjusting types need `factor` or `ratio_num`/`ratio_den`.  
Ordinary `dividend` rows are stored but **not** used for V1 price-return adjustment.

### trading_calendar
Required: `session_date,is_open`  
Optional: `source`

### symbol_isin_map
Required: `isin,symbol`  
Optional: `valid_from,valid_to`

## Output layout

```text
data/clean/l0/...   # normalized, unadjusted
data/clean/l1/...   # canonical research (consume this later)
data/raw/...        # immutable + SHA-256 sidecars
data/metadata/...   # runs, manifests, pipeline state
```

## Run

```bash
uv run stock-engine-ingest --as-of YYYY-MM-DD
```

Data dictionaries: [`dictionary/`](dictionary/).
