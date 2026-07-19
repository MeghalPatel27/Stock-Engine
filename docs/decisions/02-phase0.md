# ADR 02 — Phase 0: Foundations & Cross-Cutting Architecture

**Status:** Finalized  
**Date locked:** 2026-07-19  
**Supersedes:** [02-phase0-proposal.md](02-phase0-proposal.md) (proposal archive)  
**Depends on:** [00-philosophy.md](00-philosophy.md), [01-phase1.md](01-phase1.md)

Sign-off amendments vs original proposal:
1. Add `scripts/` for developer/ops utilities (not production package code).
2. Persist `config_version` + `config_hash` on every engine run.
3. Every execution gets a unique `run_id`; logs include `run_id`, `as_of_date`, `pipeline_stage` when applicable.
4. Reserve `data/metadata/` for manifests, dataset versions, config hashes, run metadata, pipeline state.
5. Introduce `RunMetadata` contract early.
6. Post-approve path: **minimal scaffold first**, then Phase 2 design (no ingestion code yet).
7. mypy recommended later; not blocking Phase 0.

---

## 1. Context

Lock the engineering foundation so research and (eventual) production code share one reproducible local-first Python monorepo, without overbuilding cloud/MLOps.

---

## 2. Decision summary (locked)

| Area | Decision |
|---|---|
| Language | Python **3.11+** only for V1 |
| Layout | Monorepo: `src/`, `research/`, `tests/`, `docs/`, `config/`, `scripts/`, `data/` |
| Deps | **uv** + lockfile |
| Secrets | `.env` + `.env.example`; secrets gitignored |
| Compute | **Local-first** (laptop); cloud only if necessary |
| Budget | ≤ **₹2–5k/month**; prefer free/open |
| Quality bar | Ruff + format + unit tests + **GitHub Actions CI** |
| Separation | Strict `research/` vs `src/`; `scripts/` ≠ production package |
| Config | `default.yaml` + optional `local.yaml` + env; every run stores `config_version` + `config_hash` |
| Contracts | Pydantic v2: Signal, RankRow, **RunMetadata**; no probability simplex invariant |
| Logging | stdlib; every run has `run_id`; logs carry `run_id`, `as_of_date`, `pipeline_stage` |
| ADR process | Every architectural lock under `docs/decisions/` |

---

## 3. Repository layout

```text
Stock-Engine/
├── README.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── .github/workflows/ci.yml
├── config/
│   ├── default.yaml
│   └── README.md
├── docs/
│   ├── PROJECT_CHARTER.md
│   └── decisions/
├── src/stock_engine/
│   ├── contracts/          # Signal, RankRow, RunMetadata, …
│   ├── config/             # load/merge config + hash
│   └── logging_utils/      # run_id-aware logging bootstrap
├── research/
│   ├── notebooks/
│   └── experiments/
├── scripts/                # developer utilities only
│   ├── bootstrap.py
│   └── clean.py
├── tests/
│   ├── unit/
│   └── contracts/
└── data/                   # gitignored contents; .gitkeep retained
    ├── raw/
    ├── clean/
    ├── features/
    └── metadata/           # manifests, versions, run metadata, pipeline state
```

### Rules

1. `src/stock_engine` never imports from `research/` or `scripts/`.  
2. `research/` and `scripts/` may import from `src/stock_engine`.  
3. No notebooks under `src/`.  
4. Thresholds live in `config/`, not magic numbers.  
5. Operational one-offs go in `scripts/`, never in `src/`.  
6. Feature/raw/clean data never mixed with `data/metadata/`.

---

## 4. Dependency management

- **uv** + committed `uv.lock`  
- Deps in `pyproject.toml`; `requires-python = ">=3.11"`  
- Dev group separate from runtime  

---

## 5. Configuration system

### Layers (highest wins)

1. `config/default.yaml` — committed defaults  
2. Optional `config/local.yaml` — gitignored  
3. Environment variables — secrets, paths, flags  

### Run reproducibility (required)

Every engine run must persist in run metadata / `data/metadata/`:

- `config_version`
- `config_hash` (hash of effective merged config)

---

## 6. Typing & contracts

- Pydantic v2 for all IO contracts  
- Public APIs type-annotated  
- **No** engine-level requirement that probabilities sum to 1  

### Required early contracts

**Signal:** `{value, direction, confidence, timestamp, version}`  

**RankRow:** required `symbol`, `as_of_date`, `horizon`, `p_bullish`, `p_bearish`, `risk`, `confidence`, `rank_long`, `rank_short`, `model_version`, `config_version`; optional `p_neutral`  

**RunMetadata:**

| Field | Purpose |
|---|---|
| `run_id` | Unique execution id |
| `as_of_date` | Decision / data as-of date |
| `config_hash` | Effective config fingerprint |
| `config_version` | Human/config schema version |
| `engine_version` | Package version |
| `timestamp` | Run start (UTC) |

---

## 7. Logging

- stdlib `logging`, structured-friendly  
- Unique `run_id` per execution  
- Every log line includes `run_id`, `as_of_date`, and `pipeline_stage` when applicable  

---

## 8. Testing, lint, packaging, CI

| Item | Locked |
|---|---|
| Tests | pytest; unit + contract tests |
| Lint/format | Ruff + Ruff format |
| Typing checker | mypy later (non-blocking) |
| Package | `stock_engine`, local-first |
| CI | GitHub Actions: uv sync, ruff, pytest on PR/`main` |

---

## 9. ADR process

Statuses: Proposed → Finalized | Superseded | Rejected.  
No important architecture only in chat.

---

## 10. Post-Phase-0 sequencing (locked)

1. Minimal scaffold (this commit series) — **no business / ingestion logic**  
2. **Phase 2 design ADR** (data acquisition) for review  
3. No market-data ingestion or modeling until Phase 2 is approved  

---

## 11. Sign-off record

Approved 2026-07-19 with amendments above; §15 pick **A** (scaffold then Phase 2 design).
