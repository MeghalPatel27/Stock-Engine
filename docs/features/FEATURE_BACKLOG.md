# Feature backlog (V1 ranking engine)

Planned features for the daily post-close Top Longs / Top Shorts engine.  
Naming: `{domain}__{metric}__{params}` · windows in **trading sessions**.

**Status key:** ✅ done · ⏭️ next · 📋 planned · ⏸️ later / optional

---

## 0. Raw / foundation (`family: other`)

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `raw__close_adj__l1@v1` | raw | ✅ | L1 adjusted close projection |
| `raw__volume_adj__l1@v1` | raw | 📋 | Needed before ADV / liquidity |
| `raw__traded_value__l1@v1` | raw | 📋 | Optional; helps ADV in INR |

---

## 1. Momentum (`family: momentum`)

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `mom__ret__1d@v1` | rolling | ✅ | 1-session simple return |
| `mom__ret__5d@v1` | rolling | ✅ | 5-session simple return |
| `mom__ret__20d@v1` | rolling | ✅ | 20-session simple return |
| `mom__ret__60d@v1` | rolling | 📋 | Longer horizon; useful vs 5d label |
| `mom__ret__120d@v1` | rolling | ⏸️ | Optional |
| `mom__skip__21_252@v1` | rolling | ⏸️ | 12–1 style skip-month (later) |

**Next after momentum core:** trend family (below).

---

## 2. Trend (`family: trend`) — ⏭️ next family

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `trend__ema__10@v1` | rolling | 📋 | Fast EMA of `close_adj` |
| `trend__ema__20@v1` | rolling | ⏭️ | First trend feature to implement |
| `trend__ema__50@v1` | rolling | 📋 | Slow EMA |
| `trend__sma__20@v1` | rolling | 📋 | Optional SMA twin |
| `trend__sma__50@v1` | rolling | 📋 | Optional |
| `trend__price_vs_ema__20@v1` | derived | 📋 | `close / ema20 - 1` |
| `trend__ema_spread__10_50@v1` | composite | 📋 | `(ema10 - ema50) / ema50` |
| `trend__slope__ema20__5d@v1` | derived | 📋 | Short slope of EMA20 |

---

## 3. Volatility (`family: volatility`)

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `vol__std__20d@v1` | rolling | 📋 | Stdev of 1d returns (20 sessions) |
| `vol__std__60d@v1` | rolling | 📋 | Longer realized vol |
| `vol__parkinson__20d@v1` | rolling | ⏸️ | Needs high/low adj |
| `vol__atr__14@v1` | rolling | ⏸️ | Needs OHLC adj |
| `vol__range__20d@v1` | rolling | ⏸️ | (high-low)/close style |

---

## 4. Liquidity (`family: liquidity`)

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `liq__adv__20d@v1` | rolling | 📋 | Avg traded value or volume×price, 20d |
| `liq__adv__60d@v1` | rolling | 📋 | Longer ADV |
| `liq__turnover__20d@v1` | rolling | ⏸️ | If shares outstanding available |
| `liq__amihud__20d@v1` | rolling | ⏸️ | Illiquidity proxy |

Depends on `raw__volume_adj__l1` and/or `traded_value`.

---

## 5. Cross-sectional (`family: cross_sectional`)

Built **after** a stable set of single-name features exists.

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `cs__zscore__mom__ret__5d@v1` | cross_sectional | 📋 | Universe z-score of 5d return |
| `cs__zscore__mom__ret__20d@v1` | cross_sectional | 📋 | |
| `cs__rank__mom__ret__5d@v1` | cross_sectional | 📋 | Percentile rank in universe |
| `cs__zscore__vol__std__20d@v1` | cross_sectional | 📋 | |
| `cs__zscore__liq__adv__20d@v1` | cross_sectional | 📋 | |
| `cs__zscore__trend__price_vs_ema__20@v1` | cross_sectional | 📋 | |

Universe = Phase-1 liquid F&O filter as-of T (wire when CS features land).

---

## 6. Market structure (`family: market_structure`)

| Feature id | Type | Status | Notes |
|---|---|---|---|
| `mkt__gap__1d@v1` | derived | ⏸️ | Open vs prior close (needs open_adj) |
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
| RSI / MACD / Stochastic / Bollinger | Complex; validate simple returns/EMA/vol first |
| ML-generated features | After labels + modeling ADR |
| Intraday / tick features | V1 is daily post-close |
| Alternative data | Out of V1 scope |

---

## Suggested build order

1. ✅ Raw close + mom 1d / 5d / 20d  
2. ⏭️ `trend__ema__20` → `trend__price_vs_ema__20` → `trend__ema__50` / spread  
3. `vol__std__20d` (+ optional 60d)  
4. `raw__volume_adj__l1` → `liq__adv__20d`  
5. Cross-sectional z-scores/ranks of the above  
6. Promote stable ones `experimental` → `candidate` → `production`  
7. **Label Generation ADR** (can start once CS + a few families exist)

---

## Currently registered (done)

- `raw__close_adj__l1@v1`  
- `mom__ret__1d@v1`  
- `mom__ret__5d@v1`  
- `mom__ret__20d@v1`  
