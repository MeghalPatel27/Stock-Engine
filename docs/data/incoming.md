# Local CSV ingest inputs

Drop files into `data/incoming/`. The pipeline archives them to `data/raw/`,
validates, and publishes Parquet under `data/clean/`.

## Filenames

| Dataset | Accepted names |
|---|---|
| Equity EOD (required) | `equity_eod.csv` or `equity_eod__YYYY-MM-DD.csv` |
| Corporate actions (required) | `corporate_actions.csv` or `corporate_actions__YYYY-MM-DD.csv` |
| Symbol ↔ ISIN map (optional) | `symbol_isin_map.csv` or dated form |

## Required columns

### equity_eod
`isin,symbol,session_date,close`  
Optional: `open,high,low,volume,traded_value,adj_close`

### corporate_actions
`isin,ex_date,action_type`  
Optional: `symbol,ratio_num,ratio_den,factor,notes`

### symbol_isin_map
`isin,symbol`  
Optional: `valid_from,valid_to`

**Canonical id is ISIN.** `symbol` is for display / secondary mapping.

## Run

```bash
uv sync --extra dev
# copy your CSVs into data/incoming/
uv run stock-engine-ingest
# or
uv run python scripts/run_ingest.py
```
