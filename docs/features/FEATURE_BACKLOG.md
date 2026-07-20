# Feature backlog (V1 ranking engine)

Planned features for the daily post-close Top Longs / Top Shorts engine.  
Naming: `{domain}__{metric}__{params}` · windows in **trading sessions**.

**Status key:** ✅ done · 📋 planned · ⏸️ later / optional

---

## 0. Raw / foundation (`family: other`)

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `raw__close_adj__l1@v1` | raw | ✅ | L1 adjusted close projection |
| `raw__volume_adj__l1@v1` | raw | ✅ | Needed before ADV / liquidity |
| `raw__traded_value__l1@v1` | raw | ✅ | INR ADV input |

---

## 1. Momentum (`family: momentum`)

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `mom__ret__1d@v1` | rolling | ✅ | 1-session simple return |
| `mom__ret__5d@v1` | rolling | ✅ | 5-session simple return |
| `mom__ret__20d@v1` | rolling | ✅ | 20-session simple return |
| `mom__ret__60d@v1` | rolling | ✅ | Longer horizon |
| `mom__ret__120d@v1` | rolling | ⏸️ | Optional |
| `mom__skip__21_252@v1` | rolling | ⏸️ | 12–1 style skip-month (later) |

---

## 2. Trend (`family: trend`)

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `trend__ema__10@v1` | rolling | ✅ | Fast EMA of `close_adj` |
| `trend__ema__20@v1` | rolling | ✅ | |
| `trend__ema__50@v1` | rolling | ✅ | Slow EMA |
| `trend__sma__20@v1` | rolling | ✅ | |
| `trend__sma__50@v1` | rolling | ✅ | |
| `trend__price_vs_ema__20@v1` | derived | ✅ | `close / ema20 - 1` |
| `trend__ema_spread__10_50@v1` | composite | ✅ | `(ema10 - ema50) / ema50` |
| `trend__slope__ema20__5d@v1` | derived | ✅ | `ema20[T]/ema20[T-5]-1` |
| `trend__rsi__14@v1` | rolling | ✅ | Wilder RSI on `close_adj` |
| `trend__macd__12_26_9@v1` | rolling | ✅ | EMA(12) − EMA(26) |
| `trend__macd_signal__12_26_9@v1` | derived | ✅ | EMA(9) of MACD line |
| `trend__macd_hist__12_26_9@v1` | derived | ✅ | MACD − signal |

---

## 3. Volatility (`family: volatility`)

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `vol__std__20d@v1` | rolling | ✅ | Stdev of 1d returns (20 sessions) |
| `vol__std__60d@v1` | rolling | ✅ | Longer realized vol |
| `vol__parkinson__20d@v1` | rolling | ⏸️ | Needs high/low adj |
| `vol__atr__14@v1` | rolling | ⏸️ | Needs OHLC adj |
| `vol__range__20d@v1` | rolling | ⏸️ | (high-low)/close style |

---

## 4. Liquidity (`family: liquidity`)

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `liq__adv__20d@v1` | rolling | ✅ | 20d mean traded value (INR) |
| `liq__adv__60d@v1` | rolling | ✅ | Longer ADV |
| `liq__turnover__20d@v1` | rolling | ⏸️ | If shares outstanding available |
| `liq__amihud__20d@v1` | rolling | ⏸️ | Illiquidity proxy |

---

## 5. Cross-sectional (`family: cross_sectional`)

Universe V1 = all ISINs present in the panel on session T (Phase-1 F&O filter wiring later).

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `cs__zscore__mom__ret__5d@v1` | cross_sectional | ✅ | |
| `cs__zscore__mom__ret__20d@v1` | cross_sectional | ✅ | |
| `cs__rank__mom__ret__5d@v1` | cross_sectional | ✅ | Percentile rank |
| `cs__zscore__vol__std__20d@v1` | cross_sectional | ✅ | |
| `cs__zscore__liq__adv__20d@v1` | cross_sectional | ✅ | |
| `cs__zscore__trend__price_vs_ema__20@v1` | cross_sectional | ✅ | |

---

## 6. Market structure (`family: market_structure`)

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `mkt__gap__1d@v1` | derived | ⏸️ | Open vs prior close |
| `mkt__intraday_ret__1d@v1` | derived | ⏸️ | Close vs open |

---

## 7. Regime (`family: regime`) — later

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `reg__index_vol__20d@v1` | rolling | ⏸️ | Needs index series |
| `reg__breadth__adv_dec@v1` | cross_sectional | ⏸️ | Market breadth |

---

## Explicitly deferred (do not build yet)

| Idea | Why deferred |
|---|---|
| Stochastic / Bollinger | After RSI/MACD baseline validated |
| ML-generated features | After labels + modeling ADR |
| Intraday / tick features | V1 is daily post-close |
| Alternative data | Out of V1 scope |

---

## Suggested next steps

1. ✅ Planned backlog (29 features) implemented  
2. ✅ Label Generation ADR + H=5 pipeline (E2E **APPROVED**)  
3. ✅ Modeling ADR + PICK A  
4. ✅ Backtesting ADR + real-data harness  
5. ✅ Inference ADR + local RankRow publish  
6. Promote stable features `experimental` → `candidate` → `production`  
7. Wire Phase-1 universe into CS features  
8. Live-trading ADR (brokers) — later

---

## Currently registered (29)

See `docs/features/registry/*.yaml` and `FEATURE_COMPUTERS` in `src/stock_engine/features/compute/__init__.py`.
