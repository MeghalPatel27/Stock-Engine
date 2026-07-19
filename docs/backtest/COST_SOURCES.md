# Backtest cost parameter sources

Defaults live in `config/default.yaml` under `backtest.costs`.  
Do **not** invent rates — update this table when statutes/exchange circulars change.

| Parameter | Config key | Value | Authority |
|---|---|---|---|
| STT (delivery equity) | `stt_rate` | 0.001 (0.10%) buy & sell | [NSE STT & levies](https://www.nseindia.com/static/invest/first-time-investor-sebi-turnover-fees-stt-other-levies) |
| Stamp duty (delivery) | `stamp_duty_rate` | 0.00015 (0.015%) buy | [NSE Stamp duty](https://www.nseindia.com/static/invest/first-time-investor-stamp-duty-charges-taxes) |
| NSE transaction charge | `exchange_txn_rate` | 0.0000297 (0.00297%) / side | NSE cash equity schedule FY 2025–26 (member circular / broker pass-through) |
| SEBI turnover fee | `sebi_rate` | 0.000001 (₹10/crore) / side | NSE SEBI turnover fee schedule |
| GST | `gst_rate` | 0.18 on brokerage+exchange+SEBI | GST (India) |
| Brokerage (delivery) | `brokerage_rate` | 0.0 | Discount broker delivery default (configurable) |
| DP (sell) | `dp_charge_inr` | 15.34 | Broker DP tariff (Zerodha ₹13.5 + 18% GST) |
| Slippage | `slippage_bps` | 5 | Assumption for liquid large-cap F&O — **not** statutory |

Capital-gains tax is **out of scope** for V1 paper metrics (see Income Tax India materials on STT-paid equity transfers).
