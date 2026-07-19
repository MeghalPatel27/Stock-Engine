# ADR 07 — Modeling Design (Proposal)

**Status:** Proposed — awaiting explicit sign-off  
**Date:** 2026-07-19  
**Depends on:** [00-philosophy.md](00-philosophy.md), [01-phase1.md](01-phase1.md), [02-phase0.md](02-phase0.md), [05-feature-registry.md](05-feature-registry.md), [06-label-generation.md](06-label-generation.md)

**Hard rule:** No model training, RankRow emission, or backtest portfolio code until this ADR is **Finalized**.

**Gate status:** ADR-06 H=5 label pipeline E2E review = **APPROVE** (2026-07-19). Modeling ADR (this doc) is unblocked for documentation review only.

---

## 1. Context

Features and H=5 labels are published. The engine needs a **Modeling ADR** that defines how supervised models learn from:

```text
features(T) ⋈ labels(T, H=5)
```

…and how they emit Phase-1 `RankRow` scores **without** reading labels at inference and **without** introducing leakage via overlapping forward windows.

This ADR locks train/eval methodology, purged CV / embargo, metrics, calibration stance, feature selection philosophy, hyperparameter strategy, and the research vs production workflow. It does **not** implement training.

---

## 2. Decision summary (proposed)

| Topic | Proposed decision |
|---|---|
| Objective | Supervised CS probability of top/bottom quantile (ADR-01); ranking is the product |
| Primary horizon | **H=5 only** in V1 modeling |
| Train join | `features(T) ⋈ labels(T, H=5)` when `T+5` known |
| Inference inputs | Published **production** features (via signals) only — **never labels** |
| Model family (V1) | Tabular gradient-boosted trees with **two heads** (`p_bullish`, `p_bearish`) |
| Simplex | **Not** required (ADR-01); heads may be independent |
| CV | Walk-forward + **purged** folds + **embargo** of ≥ H sessions |
| Metrics | Primary: Top-K hit-rate / CS rank IC; secondary: calibration; PnL after costs = backtest phase |
| Calibration | V1: raw model scores OK (intentional debt); optional isotonic/Platt behind same contract |
| Feature selection | Registry lifecycle + documented allow-list; no target leakage |
| Hyperparameters | Nested inside walk-forward in `research/`; freeze into `model_version` |
| Research vs prod | Train/eval in `research/`; production loads frozen artifact + emits `RankRow` |
| Combiner | V1 single-model path wrapped as Signals; pluggable combiner interface preserved |
| First code after approve | **PICK A** — train-join + purged WF eval + artifact freeze (no live serving) |

---

## 3. Modeling objective (locked from ADR-01; restated)

| Layer | Decision |
|---|---|
| Training target | Cross-sectional probability of landing in top (long) or bottom (short) forward-return quantile |
| Not V1 target | Raw expected-return regression; risk-adjusted return as the label |
| Daily rank | Directional scores + **risk** + **confidence** modify ranking / eligibility |
| Success (product) | Risk-adjusted returns after realistic costs on Top-20 L/S (backtest ADR / later phase) |

Labels come from ADR-06 (`bullish` / `bearish` / `neutral`). Models must not redefine label semantics.

---

## 4. Train matrix & point-in-time rules

### 4.1 Join

```text
train_row(T, isin) =
    features(isin, session_date=T)
    ⋈ labels(isin, session_date=T, horizon=5)
```

A row is eligible only when the label partition knows `CloseAdj(T+5)` (label publish as-of ≥ T+5).

### 4.2 Inference (live / paper)

On decision date `D`:

1. Load features with `session_date <= D` only (already enforced by feature PIT).  
2. **Do not** load labels.  
3. Emit `RankRow` for horizon=5 among eligible names.  

### 4.3 Overlapping samples

Overlapping H=5 windows are allowed in the train matrix (simple).  
**Purged CV + embargo** (this ADR) prevent train/test leakage from overlap.

### 4.4 Production feature lifecycle

Live / paper production ranking may only consume features with lifecycle **`production`**.  
`candidate` features may be used in research paper runs only.  
`experimental` / `deprecated` are training diagnostics unless explicitly promoted.

---

## 5. Model family (proposed)

### 5.1 V1 primary model

**Gradient-boosted trees** on the tabular feature matrix (e.g. LightGBM / XGBoost / HistGradientBoosting — exact library chosen at implementation).

Rationale:

- Strong baseline for medium-width tabular CS panels (~pilot → ~F&O universe)  
- Handles missingness / nonlinear interactions without deep nets  
- Fast to retrain in walk-forward  
- Fits P3-leaning hybrid (ADR-00) without locking an end-to-end P1 architecture  

### 5.2 Heads

Emit **two scores** in `[0, 1]`:

| Head | Training encoding (proposed) |
|---|---|
| `p_bullish` | `1` if label=`bullish`, else `0` (binary) **or** ordinal/multiclass with bullish mass — confirm at sign-off |
| `p_bearish` | `1` if label=`bearish`, else `0` |

**Recommendation:** two independent binary heads (one-vs-rest). Neutral is the residual class for ranking purposes; `p_neutral` remains **optional** on `RankRow`.

### 5.3 Risk & confidence (V1)

| Field | V1 stance |
|---|---|
| `risk` | Heuristic composite from locked components (ADR-01 §4.4); weights config-tunable; **not** a second ML model yet |
| `confidence` | Heuristic composite from locked components (ADR-01 §4.5); may include model margin / leaf variance later |

Full learned risk/confidence models are deferred.

### 5.4 Ranking formula (proposed V1)

Among eligible names on `D`:

```text
score_long  = f(p_bullish, risk, confidence)   # higher → better long
score_short = f(p_bearish, risk, confidence)   # higher → better short
```

Default proposal:

```text
score_long  = p_bullish  * confidence * (1 - risk)
score_short = p_bearish  * confidence * (1 - risk)
```

Then `rank_long` / `rank_short` = dense ranks (1 = best). Exact `f` is config-versioned.

Emit Top `top_n_longs` / `top_n_shorts` (defaults 20) for paper lists; full ranks retained in run artifacts.

### 5.5 Signals / combiner boundary

V1 may have a **single primary model**, but must still:

1. Wrap directional outputs as `Signal` objects (`value`, `direction`, `confidence`, `timestamp`, `version`)  
2. Keep a **pluggable combiner** interface (identity / weighted sum today → learned stacking later)  
3. Ensure combiner **never** reads feature-store internals or labels  

This preserves ADR-00 migration to multi-signal P2.

---

## 6. Train / validation split (proposed)

### 6.1 Outer protocol: walk-forward

Time-ordered expanding or rolling training windows:

```text
Train on [T0, Tk) → Validate / test on [Tk, Tk+W)
Advance Tk by step S
```

Proposed defaults (config):

| Parameter | Default | Notes |
|---|---|---|
| Min train history | 252 sessions (~1y) | Fail if insufficient |
| Test fold width `W` | 21 sessions (~1m) | |
| Step `S` | 21 sessions | Non-overlapping test folds preferred |
| Mode | Expanding train | Rolling window optional later |

### 6.2 Inner protocol: hyperparameter search

Hyperparameters tuned **only** on data available before each test fold (nested).  
Winning params for fold `k` cannot peek at fold `k` test outcomes.

### 6.3 Final freeze

After walk-forward report is accepted:

1. Retrain on all data with known labels up to freeze date (respecting embargo if holding out a final blind window)  
2. Persist artifact + `model_version` + feature allow-list + config hash  
3. Production loads that freeze only  

---

## 7. Purged cross-validation & embargo (proposed)

H=5 labels overlap: a sample labeled at `T` uses information through `T+5`. Adjacent calendar rows are not independent.

### 7.1 Purge

When evaluating a test fold covering sessions `[Tk, Tk+W)`:

- **Drop** from training any row whose label window `[T, T+H]` overlaps the test fold’s information window.  
- Practically: purge training rows with `T > Tk - H` (and symmetrically around fold edges as needed).

### 7.2 Embargo

Add an **embargo** of `E` sessions between train and test (proposed default `E = H = 5`) so microstructure / slow features near the boundary do not leak.

```text
Train ends at Tk - H - E
Test starts at Tk
```

### 7.3 Scope

Purged CV / embargo apply to:

- Walk-forward folds  
- Any k-fold experiments in `research/`  

They are **not** a label-store concern (ADR-06).

---

## 8. Evaluation metrics (proposed)

### 8.1 Model / ranking diagnostics (Modeling phase)

| Metric | Role |
|---|---|
| CS Spearman IC of `score_long` vs forward return | Diagnostic |
| CS Spearman IC of `score_short` vs −forward return | Diagnostic |
| Top-K hit-rate (K=20): fraction of Top-K longs that were `bullish` | Primary ranking quality |
| Bottom-K / short hit-rate vs `bearish` | Primary ranking quality |
| Per-fold stability (IC mean / std across WF folds) | Robustness |

### 8.2 Calibration (secondary)

| Metric | Role |
|---|---|
| Reliability diagram / ECE for `p_bullish`, `p_bearish` | Secondary |
| Brier score (per head) | Secondary |

### 8.3 Economic evaluation (explicitly later)

Portfolio PnL, costs, turnover, drawdowns → **Backtesting** phase after Modeling implementation.  
Modeling ADR must not claim economic success from IC alone (ADR-01).

---

## 9. Probability calibration (proposed)

| Stance | Decision |
|---|---|
| V1 default | Ship **raw** model scores mapped into `[0,1]` (sigmoid / tree leaf probabilities). Matches ADR-00 intentional debt (“heuristic, not calibrated”). |
| Optional path | Isotonic or Platt scaling fit **inside** each walk-forward train fold only; versioned as part of `model_version` |
| Contract | Calibration must not introduce a simplex invariant |

Recommendation at sign-off: **raw scores for first model PR**; calibration as a fast follow if ECE is poor OOS.

---

## 10. Feature selection philosophy (proposed)

1. **Registry is source of truth** — only registered feature ids may enter the matrix.  
2. **Allow-list per `model_version`** — frozen list of `feature_id@version` used at train time; inference must load the same ids.  
3. **No label-derived features** — anything computed from `forward_return` / `label` is forbidden in the feature matrix.  
4. **PIT already enforced** by feature compute; modeling must not re-join future L1.  
5. **Start broad, prune by OOS** — V1 may train on the published V1 feature set (25), then drop unstable / zero-importance names in a later `model_version`.  
6. **Cross-sectional features** are allowed (they use only same-T peer data).  
7. **Missingness** — follow per-feature null policy; document model-side imputation (tree native NA vs fail).

---

## 11. Hyperparameter strategy (proposed)

| Rule | Decision |
|---|---|
| Where | `research/experiments/` only for search |
| How | Nested walk-forward; limited grid/random search |
| What is tuned | Tree depth, learning rate, subsample, min child weight, regularization, class weight / sample_weight usage |
| What is frozen | Winning params + seed + feature allow-list → `model_version` artifact metadata |
| Reproducibility | Deterministic seeds; content hash of train matrix snapshot optional |

`sample_weight` from labels (default 1.0) may be used later for regime / liquidity weighting — not required in first model.

---

## 12. Research vs production workflow (proposed)

```text
research/
  experiments/          # WF runs, sweeps, notebooks
  artifacts/            # intermediate (gitignored)
src/stock_engine/
  models/               # load frozen artifact; score → RankRow / Signals
  # never imports research/
data/models/            # published model artifacts + manifests (proposed)
```

| Step | Owner |
|---|---|
| Build train matrix | research or shared library called from research |
| Walk-forward + metrics report | research |
| Freeze artifact | explicit publish step → `data/models/{model_name}/{model_version}/` |
| Paper / live score | `src/stock_engine` loads freeze only |
| Config | `config_version` + `config_hash` on every run; `model_version` on every `RankRow` |

---

## 13. Artifact & versioning (proposed)

```text
data/models/{model_name}/{model_version}/
  model.bin                  # library-native
  feature_allowlist.json     # feature_id@version list
  train_manifest.json        # label_version, feature_set, hashes, params
  metrics_walkforward.json   # fold metrics summary
```

Bump `model_version` when: feature allow-list changes, label_version changes, head encoding changes, ranking formula changes, or train window policy changes.

Never silently overwrite a published `model_version` (same refuse-overwrite rule as labels).

---

## 14. Validation fail-closed (proposed, post-implementation)

Training / publish must fail when:

- Train matrix has duplicate `(isin, session_date)`  
- Feature allow-list id missing from feature store  
- Label horizon ≠ 5 for V1  
- Embargo / purge parameters invalid  
- Metrics report missing for freeze  
- Attempted inference path includes label columns  

---

## 15. First implementation after approval (proposed)

### PICK A (recommended) — Train matrix + purged WF + freeze

1. Train-join builder: `features(T) ⋈ labels(T, H=5)`  
2. Purged walk-forward evaluator + metrics report  
3. Single GBT two-head trainer in `research/`  
4. Artifact freeze under `data/models/`  
5. Thin production scorer: load freeze → emit `RankRow` (paper path)  
6. Unit tests for purge/embargo math + join PIT  

**Not in PICK A:** portfolio backtest engine, live serving, multi-horizon models, learned combiner, calibrated probability stack (unless trivial).

### PICK B — Design-only longer hold

Keep docs only until a second modeling review; no train-join code.

### PICK C — Full paper stack in one go

PICK A + naive costed Top-20 paper PnL harness. Higher scope risk; not recommended before backtest ADR.

---

## 16. Explicit non-goals

- No live broker integration  
- No H=1 / H=20 models yet  
- No blended multi-horizon rank  
- No engine-level probability simplex  
- No Feast / external feature platform  
- No production `phase1_filters` universe requirement for first model (pilot / `l1_intersection` OK for research; document that pilot metrics are **not** production benchmarks — same warning as labels)  
- No purged-CV implementation inside the label store  

---

## 17. Roadmap position

1. ✅ ADR-00 … ADR-06 (+ H=5 labels E2E **APPROVE**)  
2. **→ ADR-07 Modeling (this proposal)**  
3. Modeling implementation (after Finalized)  
4. Backtesting ADR / harness  
5. Inference → Serving  

---

## 18. Open choices for sign-off

Please explicitly choose:

1. **Head encoding:** independent binary heads (recommended) vs single multiclass ternary  
2. **Calibration:** defer (recommended) vs require isotonic in V1  
3. **First impl:** PICK A / B / C  
4. **Train window:** expanding (recommended) vs rolling  
5. **Ranking formula:** accept `p * confidence * (1-risk)` as V1 default or propose alternate  

---

## 19. Sign-off checklist

```text
§2 Decision summary table: APPROVE / CHANGE: ...
§3 Objective restatement: APPROVE / CHANGE: ...
§4 Train join + inference PIT: APPROVE / CHANGE: ...
§5 Model family + heads + ranking formula: APPROVE / CHANGE: ...
§6 Walk-forward split: APPROVE / CHANGE: ...
§7 Purged CV + embargo: APPROVE / CHANGE: ...
§8 Evaluation metrics: APPROVE / CHANGE: ...
§9 Calibration stance: APPROVE / CHANGE: ...
§10 Feature selection philosophy: APPROVE / CHANGE: ...
§11 Hyperparameter strategy: APPROVE / CHANGE: ...
§12 Research vs production workflow: APPROVE / CHANGE: ...
§13 Artifacts + versioning: APPROVE / CHANGE: ...
§14 Fail-closed validation: APPROVE / CHANGE: ...
§15 First impl: PICK A / PICK B / PICK C
§18 Open choices: answer 1–5
Phase / ADR-07 overall: APPROVE / HOLD
```
