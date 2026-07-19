# ADR 02 — Phase 0: Foundations & Cross-Cutting Architecture (Proposal)

**Status:** Proposed — awaiting explicit sign-off  
**Date:** 2026-07-19  
**Depends on:** [00-philosophy.md](00-philosophy.md), [01-phase1.md](01-phase1.md)  
**Inputs:** Answer pack Part 3–4 (Q11–Q23)

This is a **design proposal only**. No production application code in this phase gate. After sign-off, scaffolding may begin; **Phase 2 (data acquisition) design comes next**, still before heavy implementation of pipelines.

---

## 1. Context

Lock the engineering foundation so research and (eventual) production code share one reproducible local-first Python monorepo, without overbuilding cloud/MLOps.

---

## 2. Decision summary (proposed)

| Area | Proposal |
|---|---|
| Language | Python **3.11+** only for V1 |
| Layout | Simple monorepo: `src/`, `research/`, `tests/`, `docs/`, `config/` |
| Deps | **uv** + lockfile |
| Secrets | `.env` + `.env.example`; secrets gitignored |
| Compute | **Local-first** (laptop); cloud only if necessary; migration documented later |
| Budget | ≤ **₹2–5k/month**; prefer free/open; buy only if it saves weeks |
| Quality bar | Ruff + formatter + unit tests + **GitHub Actions CI** on every PR |
| Separation | Strict `research/` vs `src/` from day one (invariant) |
| Config | Versioned YAML/TOML for thresholds; env for secrets/paths |
| Contracts | Typed schemas for signal + daily engine outputs (implementation-agnostic) |
| ADR process | Every architectural lock lives under `docs/decisions/` |

---

## 3. Repository layout

```text
Stock-Engine/
├── README.md
├── pyproject.toml          # project metadata, deps, tool config (ruff, pytest, …)
├── uv.lock                 # locked dependencies
├── .env.example
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml          # lint + format check + tests
├── config/
│   ├── default.yaml        # adv_min, price_min, quantiles, top_n, … (non-secret)
│   └── README.md           # how overlays / env overrides work
├── docs/
│   ├── PROJECT_CHARTER.md
│   ├── QUESTIONS.md        # answered packs archived / superseded as needed
│   └── decisions/          # ADRs (this process)
├── src/
│   └── stock_engine/       # importable package — production-oriented code only
│       ├── __init__.py
│       ├── contracts/      # pydantic/msgspec schemas: Signal, RankRow, …
│       ├── config/         # load/merge config
│       └── …               # domains added per later phases (no premature packages)
├── research/
│   ├── notebooks/          # exploratory only; not imported by src
│   └── experiments/        # one-off scripts; must not be required by production entrypoints
├── tests/
│   ├── unit/
│   └── contracts/          # schema / invariant tests
└── data/                   # local artifact root (gitignored contents; keep .gitkeep)
    ├── raw/
    ├── clean/
    └── features/
```

### Rules

1. **`src/stock_engine`** may never import from `research/`.  
2. `research/` may import from `src/stock_engine` (stable contracts only).  
3. No notebooks under `src/`.  
4. Thresholds and universe knobs live in `config/`, not scattered magic numbers in code.  
5. Do not create microservice or multi-package splits in V1.

---

## 4. Dependency management

- **Tool:** [uv](https://github.com/astral-sh/uv)  
- **Declare deps in** `pyproject.toml`  
- **Lock with** `uv.lock` (committed)  
- **Dev groups:** `dev` (pytest, ruff, pre-commit optional) separate from runtime  
- **Python pin:** `requires-python = ">=3.11"`  
- Prefer well-maintained open-source libraries; paid services only inside budget and only if they save weeks (Q18).

Exact library choices for data/ML are **Phase 2+** (pandas/polars, etc. proposed when needed — not locked here beyond “Python scientific stack is allowed”).

---

## 5. Configuration system

### 5.1 Layers (highest wins)

1. `config/default.yaml` — committed defaults (`adv_min`, `price_min`, quantiles, `top_n_longs` / `top_n_shorts`, exclusion toggles, paths)  
2. Optional `config/local.yaml` — gitignored machine overrides  
3. Environment variables — secrets, absolute paths, feature flags  

### 5.2 Principles

- Every Phase 1 threshold is a **named config key** with a default (see ADR 01 §5.2).  
- Config loads once at process start; emit **config hash / version** into run metadata for reproducibility.  
- Secrets never in YAML committed to git — only in `.env`.  
- `.env.example` documents required keys with dummy values.

### 5.3 Example default keys (illustrative)

```yaml
universe:
  adv_min_inr_cr: 50
  price_min_inr: 50
  refresh: weekly
labels:
  top_quantile: 0.20
  bottom_quantile: 0.20
  horizon_primary: 5
output:
  top_n_longs: 20
  top_n_shorts: 20
```

---

## 6. Typing

- Public functions and all **contracts** fully type-annotated.  
- `py.typed` marker on the package when scaffolding lands.  
- Prefer `TypedDict` / Pydantic v2 (or msgspec) for IO schemas — **final schema library chosen at scaffolding sign-off**; proposal default: **Pydantic v2** (ecosystem + validation errors).  
- No `Any` in contract modules without a tracked exception.

---

## 7. Data & engine contracts (cross-cutting)

Independent of model implementation (user note #3; ADR 01 §4.3).

### 7.1 Signal contract (philosophy invariant #1)

```text
Signal = { value, direction, confidence, timestamp, version }
```

Combiner consumes only this shape.

### 7.2 Daily rank row contract (Phase 1 outputs)

Required: `symbol`, `as_of_date`, `horizon`, `p_bullish`, `p_bearish`, `risk`, `confidence`, `rank_long`, `rank_short`, `model_version`, `config_version`.  
Optional: `p_neutral`, explainability payloads.  

**No** engine-level assertion that probabilities sum to 1.

### 7.3 Point-in-time

Every stored feature/raw snapshot carries `as_of` / `available_at` semantics once storage exists (Phase 3). Phase 0 only reserves naming and forbids APIs that take “future” frames without explicit as-of.

---

## 8. Logging

- Standard library `logging` first (no mandatory paid vendor).  
- Structured-friendly format: timestamp, level, logger, message, optional `run_id` / `as_of`.  
- Library code logs; CLI entrypoints configure handlers.  
- Research scripts may use print; production paths must use logging.  
- Observability platforms deferred (charter V1 debt).

---

## 9. Testing

| Layer | Expectation |
|---|---|
| Unit | Pure functions, config load, contract validation |
| Contract tests | Schema accept/reject; probability sum **not** required |
| Integration | Deferred until Phase 2+ has real I/O fixtures |

- Framework: **pytest**  
- Layout: `tests/` mirrors package areas  
- No network in unit tests; fixtures under `tests/fixtures/`  

---

## 10. Linting & formatting

| Tool | Role |
|---|---|
| **Ruff** | Lint + import sort |
| **Ruff format** (or Black if preferred at scaffolding — **proposal: Ruff format** for one toolchain) | Formatting |
| Optional | `mypy` or `ty` later; not blocking V1 scaffolding if Ruff + types in contracts are solid |

CI fails on lint or format drift.

---

## 11. Packaging & entrypoints

- Installable package: `stock_engine` via `pyproject.toml`  
- V1 CLI: `python -m stock_engine ...` or console script once a command exists  
- No Docker requirement for V1 local-first; Dockerfile may be added later as docs-only migration aid  
- Version: semantic versioning starting `0.1.0` at first scaffold commit  

---

## 12. CI / quality bar (merge gate)

GitHub Actions on PR and `main`:

1. Checkout + setup Python 3.11+ via uv  
2. `uv sync --frozen`  
3. Ruff check + format check  
4. `pytest`  

Local-first execution does **not** waive CI. Pre-commit hooks optional (recommended, not required at Phase 0 lock).

---

## 13. ADR process (locked as process)

1. Every architectural decision gets an ADR under `docs/decisions/NN-slug.md`.  
2. Statuses: `Proposed` → `Finalized` | `Superseded` | `Rejected`.  
3. No important architecture only in chat — promote to ADR before the next phase.  
4. Threshold changes that alter research semantics bump `config_version` and note in changelog or a short ADR if behavioral.  
5. Phase order remains: Philosophy → Phase 1 → Phase 0 → Phase 2 → … (this proposal is Phase 0).  

Numbering:

| ID | Topic |
|---|---|
| 00 | Philosophy (finalized) |
| 01 | Phase 1 problem formulation (finalized) |
| 02 | Phase 0 foundations (this proposal) |

---

## 14. Explicit non-goals for Phase 0

- No data provider selection (Phase 2)  
- No feature store / orchestration product pick beyond “local files + future thin layer”  
- No dashboard, API server, or cloud deploy  
- No production trading execution  
- No premature multi-package monorepo tooling (Bazel, etc.)  

---

## 15. Implementation sequencing (after this ADR is approved)

Still **no Phase 2** until Phase 0 is signed off. After approval, allowed next steps in order:

1. Scaffold empty package layout + `pyproject.toml` + uv lock + CI + config defaults + contract stubs (**minimal scaffolding**, still not data pipelines).  
2. Open **Phase 2 design questions / proposal** (data acquisition).  
3. Only then implement ingestion against approved providers.

If you prefer **zero scaffolding until Phase 2 is also designed**, say so at sign-off — default recommendation is: approve Phase 0 → tiny scaffold → Phase 2 design → then real data code.

---

## 16. Sign-off checklist

```text
§3 Repo layout (src / research / tests / config / docs): APPROVE / CHANGE: ...
§4 uv + lockfile: APPROVE / CHANGE: ...
§5 Config layers (default.yaml + local + env): APPROVE / CHANGE: ...
§6 Typing + Pydantic v2 default for contracts: APPROVE / CHANGE: ...
§7 Contracts (signal + rank row; no simplex invariant): APPROVE / CHANGE: ...
§8 Logging (stdlib structured-friendly): APPROVE / CHANGE: ...
§9 pytest unit/contract tests: APPROVE / CHANGE: ...
§10 Ruff lint + format: APPROVE / CHANGE: ...
§11 Packaging (stock_engine, local-first): APPROVE / CHANGE: ...
§12 GitHub Actions CI merge gate: APPROVE / CHANGE: ...
§13 ADR process: APPROVE / CHANGE: ...
§15 After approve: minimal scaffold then Phase 2 design  OR  Phase 2 design before any scaffold: PICK A / B
Phase 0 overall: APPROVE / HOLD
```
