# ADR-05 Feature Framework — Review Packet for ChatGPT

**Repo:** MeghalPatel27/Stock-Engine  
**PR:** https://github.com/MeghalPatel27/Stock-Engine/pull/4  
**Branch:** `cursor/feature-framework-1c98`  
**Status:** CI green. Framework only (PICK B). No concrete feature formulas.

## Ask of reviewer

Answer:
1. Framework architecture — Approve / Change (registry, store, publish, DAG, schema, versioning, lifecycle)
2. Gaps before first real feature (deps, validation, cycles, caching, hashing, metadata versioning, reproducibility, PIT, incremental recompute)
3. Is registry/DAG/publish fail-closed robust enough?
4. If approved, safest first production feature (not RSI/MACD)

**Hard rule:** Do not propose implementing RSI/MACD/momentum formulas until this review passes.

---


## FILE: `docs/decisions/05-feature-registry.md`

```
# ADR 05 — Feature Registry & Feature Store

**Status:** Finalized  
**Date locked:** 2026-07-19  
**Supersedes:** [05-phase-feature-registry-proposal.md](05-phase-feature-registry-proposal.md)  
**Depends on:** [01-phase1.md](01-phase1.md), [04-phase3.md](04-phase3.md), [04-cleaning-review.md](04-cleaning-review.md)

## Sign-off amendments

1. Every feature declares **`feature_type`**: `raw` | `rolling` | `cross_sectional` | `derived` | `composite`.  
2. Optional metadata: **`computational_cost`** (`low` / `medium` / `high`), **`stability`** (`experimental` / `stable`).  
3. Organize features into **Feature Families** (momentum, trend, volatility, liquidity, …).  
4. First implementation = **PICK B — framework only** (no concrete feature compute such as `mom__ret__1d` until framework review).  

## Locked decisions

| Topic | Decision |
|---|---|
| What is a feature? | Named, versioned, typed value(s) from L1 / upstream features with lookback, PIT, and `feature_type` |
| Families | Features grouped under family ids (momentum, trend, volatility, liquidity, market_structure, cross_sectional, …) |
| Registry | YAML under `docs/features/registry/`; families in `docs/features/families.yaml` |
| Store V1 | Local Parquet under `data/features/` (no Feast/Tecton) |
| Naming | `{domain}__{metric}__{params}` |
| Versioning | Per-feature `version` (`v1`, `v2`, …); path includes version |
| PIT | Inputs with `session_date <= T` only; lookbacks use trading calendar |
| Nulls | Explicit `propagate` / `skip_row` / `fail_run` per feature |
| Lifecycle | `experimental` → `candidate` → `production` → `deprecated` |
| Validation | Fail-closed for `production` lifecycle |
| Recompute | Same L1 + registry + config → identical feature Parquet |
| Signals | Features feed signals; combiner sees **signals only** — never bypass |
| First code | Registry loader, metadata validation, DAG, storage interface, publisher + unit tests |

---

## 1. Context

L1 published datasets are the only inputs for research/production features. Before computing any indicator, we need a registry and store so features are named, versioned, point-in-time-safe, validated, and reusable — aligned with the signal contract and research/production split.

---

## 2. Decision summary

See locked table above. All §2–§15 proposals from the design review are **APPROVED**, with the sign-off amendments listed at the top.

---

## 3. What is a feature?

A **feature** is:

1. A deterministic function of one or more **published** datasets (normally L1) and/or other registered features  
2. Emitted as typed values keyed by `(isin, session_date)` unless cross-sectional-only  
3. Described by registry metadata (not tribal knowledge)  
4. Declared with an explicit **`feature_type`** for scheduling and dependency resolution  
5. Validated before publish  

A **feature set** is a versioned bundle of features computed together in one job (e.g. `alpha_v1`).

**Not features (yet):** model probabilities, ranks, labels — later phases that may *consume* features (via signals).

### Feature types

| `feature_type` | Meaning |
|---|---|
| `raw` | Thin projection / rename from a dataset |
| `rolling` | Windowed over trading sessions for one ISIN |
| `cross_sectional` | Uses the cross-section at session T |
| `derived` | Transform of one upstream feature |
| `composite` | Combines multiple upstream features |

---

## 4. Feature naming

```text
{domain}__{metric}__{params}
```

| Domain | Examples |
|---|---|
| `mom` | momentum / returns |
| `vol` | volatility |
| `liq` | liquidity |
| `trend` | MA / trend state |
| `cs` | cross-sectional rank/zscore of another feature |
| `reg` | regime inputs (later) |

Rules: lowercase; `__` separators; windows in trading days (`5d`); no ticker names inside feature names.

*(Concrete names such as `mom__ret__1d` are reserved for the Feature Implementation phase — not this framework PR.)*

---

## 5. Registry metadata

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Canonical name |
| `version` | yes | e.g. `v1` |
| `family` | yes | Family id from `families.yaml` |
| `feature_type` | yes | See §3 |
| `owner` | yes | person/role |
| `description` | yes | human meaning |
| `dtype` | yes | float / int / bool / category |
| `unit` | no | return, INR, dimensionless, … |
| `dependencies` | yes | `dataset:…` and/or `feature:…` refs |
| `lookback_sessions` | yes | max trading days of history needed |
| `pit_rule` | yes | V1: `asof_session_close` |
| `null_policy` | yes | `propagate` / `skip_row` / `fail_run` |
| `lifecycle` | yes | experimental / candidate / production / deprecated |
| `validation` | yes | finite, min/max, allow_null, … |
| `recomputable` | yes | always `true` for V1 |
| `computational_cost` | no | `low` / `medium` / `high` |
| `stability` | no | `experimental` / `stable` |

Identity: `feature_id = {name}@{version}`.

---

## 6. Feature families

Instead of a flat list, features belong to a family:

| Family id | Intent |
|---|---|
| `momentum` | Return / momentum style |
| `trend` | MA / trend state |
| `volatility` | Vol / range |
| `liquidity` | ADV / turnover / impact |
| `market_structure` | Structure inputs |
| `cross_sectional` | Ranks, z-scores, relative |
| `regime` | Regime (later) |
| `other` | Transitional |

Families live in `docs/features/families.yaml`. Unknown `family` → registry load fails. Families enable group enable/disable, importance analysis, and experiment comparison later.

---

## 7. Dependencies & DAG

- Registry forms a DAG: features may depend on L1 datasets and upstream features.  
- Cycles forbidden.  
- Compute order is a topological sort of the requested feature set.  
- Missing dependency → fail closed for that feature set publish.  

---

## 8. Lookback windows & calendar

- All windows counted in **canonical `trading_calendar`** open sessions.  
- A feature with `lookback_sessions=20` on date T requires 20 prior open sessions of inputs (or applies `null_policy`).  
- No calendar-day shortcuts that ignore holidays.  
- Framework helper: `stock_engine.features.calendar.sessions_on_or_before`.  

---

## 9. Point-in-time guarantees

1. Input only published L1 (and published upstream features) with `session_date <= T`.  
2. No use of `close_adj` from T+1 when computing T.  
3. Cross-sectional features use only the eligible universe **as-of T** (universe wiring later).  
4. Feature publish stores `as_of_date` + `config_hash` + `registry_hash`.  

---

## 10. Versioning & path layout

| Change type | Action |
|---|---|
| Bugfix with same semantics | patch note; may keep `v1` if goldens unchanged |
| Formula / window / null policy change | bump `version` → `v2`; do not overwrite `v1` outputs |
| Rename | new feature; deprecate old |

```text
data/features/{feature_set}/{feature_version}/as_of_date=YYYY-MM-DD/features.parquet
docs/features/registry/          # one YAML per feature (empty until Feature Implementation)
docs/features/families.yaml
```

---

## 11. Null handling

| Policy | When |
|---|---|
| `propagate` | Insufficient lookback → NaN; downstream decides |
| `skip_row` | Drop ISIN-date from feature set output |
| `fail_run` | Structural expectation violated (e.g. missing L1) |

Default for rolling stats: **`propagate`**. Production feature sets may tighten.

---

## 12. Validation before publish

Per feature (fail closed for `production` lifecycle):

- dtype / finite checks  
- optional min/max  
- no missing required columns  
- registry hash recorded  

Experimental features may skip value fail-closed checks (framework flag).

---

## 13. Recomputability & goldens

- Same L1 snapshot + registry + config → byte-stable feature Parquet (aside from run_id/timestamps in lineage).  
- Golden feature fixtures required when the first `production` feature set lands.  
- Lineage: `run_id`, `config_hash`, `registry_hash`, source dataset versions.  

---

## 14. Storage (V1 local Parquet)

No Feast/Tecton in V1. `FeatureStore` protocol allows a later backend swap. Publisher writes Parquet + optional metadata JSON under `data/metadata/features/published/`.

---

## 15. Lifecycle

| State | Research | Production rank |
|---|---|---|
| experimental | yes | no |
| candidate | yes | no (paper only) |
| production | yes | yes |
| deprecated | read-only | no |

---

## 16. Relation to signal contract

Features are **inputs** to signals. A signal may wrap one or more features and must still emit:

`{value, direction, confidence, timestamp, version}`

**The combiner never reads raw feature store internals — only the signal contract.** Do not bypass this abstraction.

---

## 17. First implementation (PICK B)

Implement and review **framework only**:

- Registry loader + metadata validation (`feature_type`, families, optional cost/stability)  
- Dependency DAG validation  
- Feature storage interfaces (`LocalParquetFeatureStore`)  
- Feature publishing framework (validate + write + manifest)  
- Trading-calendar lookback helper  
- Unit tests + fixture YAML under `tests/fixtures/features/`  

**Do not** implement concrete feature formulas (including `mom__ret__1d`) until the framework is reviewed.

---

## 18. Refined roadmap

1. ✅ Project Charter  
2. ✅ Phase 1 — Problem Formulation  
3. ✅ Phase 0 — Foundations  
4. ✅ Phase 2 — Data Acquisition  
5. ✅ Phase 3 — Cleaning & Normalization  
6. ✅ ADR-05 — Feature Registry & Store Design  
7. **→ Feature Framework Implementation** (registry, DAG, publishing, validation, storage)  
8. Feature Implementation (Momentum, Trend, Volatility, Liquidity, …)  
9. Label Generation ADR  
10. Label implementation  
11. Modeling ADR  
12. Model implementation  
13. Backtesting  
14. Inference  
15. Serving  

---

## Explicit non-goals (framework phase)

No RSI/MACD/momentum/volatility/liquidity compute. No labels. No models. No ranking. No backtests. No NSE downloaders in `src/`.

```


## FILE: `docs/features/families.yaml`

```
families:
  - id: momentum
    description: Return / momentum style features
  - id: trend
    description: Moving-average and trend-state features
  - id: volatility
    description: Volatility and range features
  - id: liquidity
    description: ADV, turnover, impact-style features
  - id: market_structure
    description: Market microstructure / structure inputs
  - id: cross_sectional
    description: Cross-sectional ranks, z-scores, relative features
  - id: regime
    description: Regime-related inputs (later)
  - id: other
    description: Uncategorized / transitional

```


## FILE: `docs/features/README.md`

```
# Features

## Layout

```text
docs/features/
  families.yaml              # feature families
  registry/                  # one YAML per feature (empty until Feature Implementation)
  README.md
data/features/               # published Parquet (gitignored contents)
```

## Rules (ADR-05)

- Register features before implementing compute.  
- Combiner consumes **signals**, not raw features.  
- Framework first; concrete features only after framework review.  
- Lookbacks use the canonical trading calendar.  
- Production lifecycle = fail-closed validation.  
- Every feature declares `feature_type` and a `family`.  

## Feature YAML schema

See `stock_engine.features.models.FeatureSpec` and fixtures under `tests/fixtures/features/`.

Required fields include: `name`, `version`, `family`, `feature_type`, `owner`, `description`,
`dtype`, `dependencies`, `lookback_sessions`, `pit_rule`, `null_policy`, `lifecycle`,
`validation`, `recomputable`.

Optional: `unit`, `computational_cost`, `stability`.

```


## FILE: `src/stock_engine/features/__init__.py`

```
"""Feature registry, DAG, store, and publishing framework (no feature compute)."""

from stock_engine.features.calendar import require_lookback_sessions, sessions_on_or_before
from stock_engine.features.dag import FeatureDAG, validate_dag
from stock_engine.features.models import FeatureSpec
from stock_engine.features.publish import FeaturePublishRequest, publish_feature_frame
from stock_engine.features.registry import FeatureRegistry, load_registry
from stock_engine.features.store import LocalParquetFeatureStore

__all__ = [
    "FeatureDAG",
    "FeaturePublishRequest",
    "FeatureRegistry",
    "FeatureSpec",
    "LocalParquetFeatureStore",
    "load_registry",
    "publish_feature_frame",
    "require_lookback_sessions",
    "sessions_on_or_before",
    "validate_dag",
]

```


## FILE: `src/stock_engine/features/models.py`

```
"""Pydantic models for feature registry metadata."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

FeatureType = Literal["raw", "rolling", "cross_sectional", "derived", "composite"]
Lifecycle = Literal["experimental", "candidate", "production", "deprecated"]
NullPolicy = Literal["propagate", "skip_row", "fail_run"]
ComputationalCost = Literal["low", "medium", "high"]
Stability = Literal["experimental", "stable"]
PitRule = Literal["asof_session_close"]


class FeatureValidation(BaseModel):
    finite: bool = True
    min_value: float | None = None
    max_value: float | None = None
    allow_null: bool = True


class FeatureSpec(BaseModel):
    """Machine-readable feature definition (registry entry)."""

    name: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9]*(__[a-z0-9]+)+$")
    version: str = Field(min_length=1, pattern=r"^v[0-9]+$")
    family: str = Field(min_length=1)
    feature_type: FeatureType
    owner: str = Field(min_length=1)
    description: str = Field(min_length=1)
    dtype: Literal["float", "int", "bool", "category"]
    unit: str | None = None
    dependencies: list[str] = Field(min_length=1)
    lookback_sessions: int = Field(ge=0)
    pit_rule: PitRule = "asof_session_close"
    null_policy: NullPolicy
    lifecycle: Lifecycle
    validation: FeatureValidation = Field(default_factory=FeatureValidation)
    recomputable: bool = True
    computational_cost: ComputationalCost | None = None
    stability: Stability | None = None

    @field_validator("dependencies")
    @classmethod
    def _deps_format(cls, deps: list[str]) -> list[str]:
        for d in deps:
            if not (d.startswith("dataset:") or d.startswith("feature:")):
                msg = f"Dependency must start with dataset: or feature: — got {d!r}"
                raise ValueError(msg)
        return deps

    @property
    def feature_id(self) -> str:
        return f"{self.name}@{self.version}"

    def feature_deps(self) -> list[str]:
        return [d.removeprefix("feature:") for d in self.dependencies if d.startswith("feature:")]

    def dataset_deps(self) -> list[str]:
        return [d.removeprefix("dataset:") for d in self.dependencies if d.startswith("dataset:")]


class FeatureFamily(BaseModel):
    id: str
    description: str = ""


class FamiliesFile(BaseModel):
    families: list[FeatureFamily]

    def ids(self) -> set[str]:
        return {f.id for f in self.families}


class FeatureSetManifest(BaseModel):
    """Metadata for a published feature-set Parquet."""

    feature_set: str
    feature_version: str
    as_of_date: str
    run_id: str
    config_hash: str
    config_version: str
    registry_hash: str
    feature_ids: list[str]
    row_count: int
    parquet_path: str
    extra: dict[str, Any] = Field(default_factory=dict)

```


## FILE: `src/stock_engine/features/registry.py`

```
"""Load and validate the feature registry from YAML."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from stock_engine.features.dag import validate_dag
from stock_engine.features.models import FamiliesFile, FeatureSpec


class FeatureRegistry:
    def __init__(
        self,
        features: dict[str, FeatureSpec],
        family_ids: set[str],
        *,
        root: Path,
    ) -> None:
        self._features = features
        self.family_ids = family_ids
        self.root = root

    def __contains__(self, feature_id: object) -> bool:
        return isinstance(feature_id, str) and feature_id in self._features

    def __len__(self) -> int:
        return len(self._features)

    def get(self, name: str, version: str | None = None) -> FeatureSpec:
        if version:
            key = f"{name}@{version}"
            if key not in self._features:
                msg = f"Unknown feature {key}"
                raise KeyError(msg)
            return self._features[key]
        matches = [f for f in self._features.values() if f.name == name]
        if not matches:
            msg = f"Unknown feature {name}"
            raise KeyError(msg)
        if len(matches) > 1:
            msg = f"Multiple versions for {name}; pass version explicitly"
            raise KeyError(msg)
        return matches[0]

    def all(self) -> list[FeatureSpec]:
        return sorted(self._features.values(), key=lambda f: f.feature_id)

    def active(self) -> list[FeatureSpec]:
        """Non-deprecated features (candidates for compute jobs)."""
        return [f for f in self.all() if f.lifecycle != "deprecated"]

    def by_family(self, family: str) -> list[FeatureSpec]:
        return [f for f in self.all() if f.family == family]

    def by_lifecycle(self, lifecycle: str) -> list[FeatureSpec]:
        return [f for f in self.all() if f.lifecycle == lifecycle]

    def by_feature_type(self, feature_type: str) -> list[FeatureSpec]:
        return [f for f in self.all() if f.feature_type == feature_type]

    def registry_hash(self) -> str:
        payload = [
            f.model_dump(mode="json")
            for f in sorted(self._features.values(), key=lambda x: x.feature_id)
        ]
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_registry(
    registry_dir: Path,
    families_path: Path,
    *,
    validate_graph: bool = True,
) -> FeatureRegistry:
    """
    Load family catalog + all feature YAML files.

    Raises ValueError on schema/family/DAG errors.
    """
    if not families_path.exists():
        msg = f"Missing families file: {families_path}"
        raise FileNotFoundError(msg)

    families_raw = yaml.safe_load(families_path.read_text(encoding="utf-8")) or {}
    families = FamiliesFile.model_validate(families_raw)
    family_ids = families.ids()
    if not family_ids:
        msg = "families.yaml must declare at least one family"
        raise ValueError(msg)

    features: dict[str, FeatureSpec] = {}
    errors: list[str] = []

    if registry_dir.exists():
        paths = sorted(registry_dir.glob("*.yaml")) + sorted(registry_dir.glob("*.yml"))
    else:
        paths = []

    for path in paths:
        if path.name.startswith("_"):
            continue
        if path.name in {"families.yaml", "families.yml"}:
            continue
        if path.resolve() == families_path.resolve():
            continue
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            spec = FeatureSpec.model_validate(raw)
        except (yaml.YAMLError, ValidationError, OSError) as exc:
            errors.append(f"{path.name}: {exc}")
            continue

        if spec.family not in family_ids:
            errors.append(f"{path.name}: unknown family {spec.family!r}")
            continue

        if spec.feature_id in features:
            errors.append(f"{path.name}: duplicate feature_id {spec.feature_id}")
            continue

        # Filename convention tip (not hard-required): name@version.yaml preferred
        features[spec.feature_id] = spec

    if errors:
        raise ValueError("Registry validation failed:\n- " + "\n- ".join(errors))

    registry = FeatureRegistry(features, family_ids, root=registry_dir)
    if validate_graph:
        validate_dag(registry.all())
    return registry


def default_registry_paths(repo_root: Path) -> tuple[Path, Path]:
    return (
        repo_root / "docs" / "features" / "registry",
        repo_root / "docs" / "features" / "families.yaml",
    )

```


## FILE: `src/stock_engine/features/dag.py`

```
"""Feature dependency DAG validation (cycles forbidden)."""

from __future__ import annotations

from collections import defaultdict, deque

from stock_engine.features.models import FeatureSpec


class FeatureDAG:
    """Directed graph: edge A→B means B depends on A (A must compute first)."""

    def __init__(self, features: list[FeatureSpec]) -> None:
        self.features = {f.feature_id: f for f in features}
        self.edges: dict[str, set[str]] = defaultdict(set)  # dep -> dependents
        self.reverse: dict[str, set[str]] = defaultdict(set)  # feature -> feature deps

        # Prefer exact feature:name@version; allow feature:name if unique
        by_name: dict[str, list[str]] = defaultdict(list)
        for f in features:
            by_name[f.name].append(f.feature_id)

        for f in features:
            for dep in f.feature_deps():
                if "@" in dep:
                    dep_id = dep
                else:
                    ids = by_name.get(dep, [])
                    if len(ids) != 1:
                        msg = (
                            f"{f.feature_id} depends on feature:{dep} "
                            f"but found {len(ids)} versions; use name@version"
                        )
                        raise ValueError(msg)
                    dep_id = ids[0]
                if dep_id not in self.features:
                    msg = f"{f.feature_id} missing dependency feature:{dep}"
                    raise ValueError(msg)
                self.edges[dep_id].add(f.feature_id)
                self.reverse[f.feature_id].add(dep_id)

    def topological_order(self) -> list[str]:
        indeg = {fid: 0 for fid in self.features}
        for _src, dsts in self.edges.items():
            for d in dsts:
                indeg[d] += 1
        q = deque(sorted([fid for fid, n in indeg.items() if n == 0]))
        order: list[str] = []
        while q:
            n = q.popleft()
            order.append(n)
            for m in sorted(self.edges.get(n, ())):
                indeg[m] -= 1
                if indeg[m] == 0:
                    q.append(m)
        if len(order) != len(self.features):
            msg = "Feature dependency cycle detected"
            raise ValueError(msg)
        return order


def validate_dag(features: list[FeatureSpec]) -> FeatureDAG:
    """Build DAG and ensure acyclic + resolvable feature deps."""
    dag = FeatureDAG(features)
    dag.topological_order()
    return dag

```


## FILE: `src/stock_engine/features/store.py`

```
"""Feature store interfaces and local Parquet implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd


class FeatureStore(Protocol):
    def write(
        self,
        frame: pd.DataFrame,
        *,
        feature_set: str,
        feature_version: str,
        as_of_date: str,
    ) -> Path: ...

    def read(
        self,
        *,
        feature_set: str,
        feature_version: str,
        as_of_date: str,
    ) -> pd.DataFrame: ...

    def exists(
        self,
        *,
        feature_set: str,
        feature_version: str,
        as_of_date: str,
    ) -> bool: ...


class LocalParquetFeatureStore:
    """
    data/features/{feature_set}/{feature_version}/as_of_date=YYYY-MM-DD/features.parquet
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, feature_set: str, feature_version: str, as_of_date: str) -> Path:
        return (
            self.root
            / feature_set
            / feature_version
            / f"as_of_date={as_of_date}"
            / "features.parquet"
        )

    def write(
        self,
        frame: pd.DataFrame,
        *,
        feature_set: str,
        feature_version: str,
        as_of_date: str,
    ) -> Path:
        required = {"isin", "session_date"}
        missing = required - set(frame.columns)
        if missing:
            msg = f"Feature frame missing columns: {sorted(missing)}"
            raise ValueError(msg)

        out = frame.copy()
        # Deterministic order
        sort_cols = [c for c in ("isin", "session_date") if c in out.columns]
        out = out.sort_values(sort_cols).reset_index(drop=True)

        path = self._path(feature_set, feature_version, as_of_date)
        path.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(path, index=False)
        return path

    def read(
        self,
        *,
        feature_set: str,
        feature_version: str,
        as_of_date: str,
    ) -> pd.DataFrame:
        path = self._path(feature_set, feature_version, as_of_date)
        if not path.exists():
            msg = f"Feature set not found: {path}"
            raise FileNotFoundError(msg)
        return pd.read_parquet(path)

    def exists(
        self,
        *,
        feature_set: str,
        feature_version: str,
        as_of_date: str,
    ) -> bool:
        return self._path(feature_set, feature_version, as_of_date).exists()

```


## FILE: `src/stock_engine/features/publish.py`

```
"""Feature publishing framework — writes store + metadata (no compute)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.features.models import FeatureSetManifest, FeatureSpec
from stock_engine.features.registry import FeatureRegistry
from stock_engine.features.store import FeatureStore, LocalParquetFeatureStore

KEY_COLUMNS = ("isin", "session_date")


@dataclass(frozen=True)
class FeaturePublishRequest:
    feature_set: str
    feature_version: str
    as_of_date: date
    run_id: str
    config_hash: str
    config_version: str
    feature_ids: list[str]
    frame: pd.DataFrame


def _is_ok_finite(x: object) -> bool:
    try:
        value = float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return bool(pd.notna(value) and abs(value) != float("inf"))


def validate_publish_frame(
    frame: pd.DataFrame,
    specs: list[FeatureSpec],
    *,
    production_fail_closed: bool = True,
) -> list[str]:
    """
    Validate a precomputed feature frame against registry specs.

    Returns list of error strings (empty if ok). Missing key/feature columns
    always error. Value checks fail-closed for ``production`` lifecycle when
    ``production_fail_closed`` is True.
    """
    errors: list[str] = []
    for col in KEY_COLUMNS:
        if col not in frame.columns:
            errors.append(f"missing key column {col}")

    for spec in specs:
        if spec.name not in frame.columns:
            errors.append(f"missing feature column {spec.name} for {spec.feature_id}")
            continue

        if not (production_fail_closed and spec.lifecycle == "production"):
            continue

        series = frame[spec.name]
        nums = pd.to_numeric(series, errors="coerce")

        if spec.validation.finite:
            bad = series.notna() & (~nums.map(_is_ok_finite))
            if bool(bad.any()):
                errors.append(f"{spec.feature_id}: non-finite values")

        if spec.validation.min_value is not None and bool(
            (nums.notna() & (nums < spec.validation.min_value)).any()
        ):
            errors.append(f"{spec.feature_id}: below min_value")

        if spec.validation.max_value is not None and bool(
            (nums.notna() & (nums > spec.validation.max_value)).any()
        ):
            errors.append(f"{spec.feature_id}: above max_value")

        if not spec.validation.allow_null and bool(series.isna().any()):
            errors.append(f"{spec.feature_id}: nulls not allowed")

    return errors


def _resolve_specs(registry: FeatureRegistry, feature_ids: list[str]) -> list[FeatureSpec]:
    specs: list[FeatureSpec] = []
    for fid in feature_ids:
        if "@" not in fid:
            msg = f"feature_id must be name@version, got {fid!r}"
            raise ValueError(msg)
        name, ver = fid.split("@", 1)
        specs.append(registry.get(name, ver))
    return specs


def publish_feature_frame(
    request: FeaturePublishRequest,
    registry: FeatureRegistry,
    *,
    store: FeatureStore | None = None,
    features_root: Path | None = None,
    metadata_root: Path | None = None,
) -> FeatureSetManifest:
    """
    Publish an already-computed feature frame.

    This framework does not compute features — callers supply ``request.frame``.
    """
    specs = _resolve_specs(registry, request.feature_ids)
    errors = validate_publish_frame(request.frame, specs)
    if errors:
        raise ValueError("Publish validation failed:\n- " + "\n- ".join(errors))

    if store is not None:
        store_impl: FeatureStore = store
    else:
        if features_root is None:
            msg = "features_root or store is required"
            raise ValueError(msg)
        store_impl = LocalParquetFeatureStore(features_root)

    as_of = request.as_of_date.isoformat()
    path = store_impl.write(
        request.frame,
        feature_set=request.feature_set,
        feature_version=request.feature_version,
        as_of_date=as_of,
    )

    manifest = FeatureSetManifest(
        feature_set=request.feature_set,
        feature_version=request.feature_version,
        as_of_date=as_of,
        run_id=request.run_id,
        config_hash=request.config_hash,
        config_version=request.config_version,
        registry_hash=registry.registry_hash(),
        feature_ids=list(request.feature_ids),
        row_count=len(request.frame),
        parquet_path=str(path),
    )

    if metadata_root is not None:
        dest = (
            metadata_root
            / "features"
            / "published"
            / as_of
            / f"{request.feature_set}__{request.feature_version}.json"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return manifest

```


## FILE: `src/stock_engine/features/calendar.py`

```
"""Trading-calendar lookback helpers (no feature formulas)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

import pandas as pd


def _to_timestamp(value: date | datetime | pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.normalize()


CalendarLike = Sequence[date | datetime | pd.Timestamp] | pd.DatetimeIndex


def open_sessions(calendar: CalendarLike) -> pd.DatetimeIndex:
    """Normalize a calendar to ascending unique session timestamps."""
    idx = pd.DatetimeIndex(pd.to_datetime(list(calendar))).normalize().unique().sort_values()
    return idx


def sessions_on_or_before(
    calendar: CalendarLike,
    as_of: date | datetime | pd.Timestamp,
    *,
    n: int | None = None,
) -> pd.DatetimeIndex:
    """
    Return open sessions with session_date <= as_of (ascending).

    If ``n`` is set, return at most the last ``n`` such sessions (still ascending).
    """
    if n is not None and n < 0:
        msg = "n must be >= 0"
        raise ValueError(msg)

    sessions = open_sessions(calendar)
    cutoff = _to_timestamp(as_of)
    eligible = sessions[sessions <= cutoff]
    if n is None:
        return eligible
    if n == 0:
        return eligible[:0]
    return eligible[-n:]


def require_lookback_sessions(
    calendar: CalendarLike,
    as_of: date | datetime | pd.Timestamp,
    lookback_sessions: int,
) -> pd.DatetimeIndex:
    """
    Return exactly ``lookback_sessions`` sessions ending at as_of (inclusive).

    Raises ValueError if the calendar cannot satisfy the lookback (caller may
    map this to a feature null_policy later).
    """
    if lookback_sessions < 0:
        msg = "lookback_sessions must be >= 0"
        raise ValueError(msg)
    if lookback_sessions == 0:
        return open_sessions(calendar)[:0]

    window = sessions_on_or_before(calendar, as_of, n=lookback_sessions)
    if len(window) < lookback_sessions:
        msg = (
            f"Insufficient trading sessions for lookback={lookback_sessions} "
            f"as_of={pd.Timestamp(as_of).date().isoformat()} "
            f"(have {len(window)})"
        )
        raise ValueError(msg)
    return window

```


## FILE: `tests/fixtures/features/families.yaml`

```
families:
  - id: momentum
    description: Return / momentum style features
  - id: other
    description: Fixture / transitional

```


## FILE: `tests/fixtures/features/registry/fw__base__panel.yaml`

```
name: fw__base__panel
version: v1
family: other
feature_type: raw
owner: framework-tests
description: Fixture base panel (no real formula — framework tests only)
dtype: float
unit: dimensionless
dependencies:
  - dataset:l1.equity_eod
lookback_sessions: 1
pit_rule: asof_session_close
null_policy: propagate
lifecycle: experimental
validation:
  finite: true
  allow_null: true
recomputable: true
computational_cost: low
stability: experimental

```


## FILE: `tests/fixtures/features/registry/fw__child__panel.yaml`

```
name: fw__child__panel
version: v1
family: other
feature_type: derived
owner: framework-tests
description: Fixture child panel depending on fw__base__panel
dtype: float
dependencies:
  - feature:fw__base__panel@v1
lookback_sessions: 1
pit_rule: asof_session_close
null_policy: propagate
lifecycle: candidate
validation:
  finite: true
  allow_null: true
recomputable: true

```


## FILE: `tests/fixtures/features/prod/registry/fw__prod__panel.yaml`

```
name: fw__prod__panel
version: v1
family: other
feature_type: rolling
owner: framework-tests
description: Production lifecycle fixture for fail-closed validation
dtype: float
dependencies:
  - dataset:l1.equity_eod
lookback_sessions: 2
pit_rule: asof_session_close
null_policy: fail_run
lifecycle: production
validation:
  finite: true
  min_value: 0.0
  max_value: 1.0
  allow_null: false
recomputable: true
computational_cost: medium
stability: stable

```


## FILE: `tests/unit/features/test_registry.py`

```
"""Feature registry loader + metadata validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from stock_engine.features.models import FeatureSpec
from stock_engine.features.registry import load_registry

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "features"


def test_load_fixture_registry() -> None:
    registry = load_registry(FIXTURES / "registry", FIXTURES / "families.yaml")
    assert len(registry) == 2
    assert "fw__base__panel@v1" in registry
    base = registry.get("fw__base__panel", "v1")
    assert base.feature_type == "raw"
    assert base.family == "other"
    assert base.computational_cost == "low"
    assert base.stability == "experimental"
    child = registry.get("fw__child__panel")
    assert child.feature_deps() == ["fw__base__panel@v1"]
    assert registry.by_family("other")
    assert registry.registry_hash()


def test_repo_registry_empty_is_valid() -> None:
    root = Path(__file__).resolve().parents[3]
    registry = load_registry(
        root / "docs" / "features" / "registry",
        root / "docs" / "features" / "families.yaml",
    )
    assert len(registry) == 0
    assert registry.family_ids


def test_unknown_family_fails(tmp_path: Path) -> None:
    families = tmp_path / "families.yaml"
    families.write_text("families:\n  - id: momentum\n    description: x\n", encoding="utf-8")
    reg = tmp_path / "registry"
    reg.mkdir()
    (reg / "bad.yaml").write_text(
        """
name: fw__bad__family
version: v1
family: not_a_family
feature_type: raw
owner: t
description: bad family
dtype: float
dependencies:
  - dataset:l1.equity_eod
lookback_sessions: 0
pit_rule: asof_session_close
null_policy: propagate
lifecycle: experimental
validation:
  finite: true
  allow_null: true
recomputable: true
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown family"):
        load_registry(reg, families)


def test_feature_type_required() -> None:
    with pytest.raises(ValidationError):
        FeatureSpec.model_validate(
            {
                "name": "fw__no__type",
                "version": "v1",
                "family": "other",
                "owner": "t",
                "description": "missing feature_type",
                "dtype": "float",
                "dependencies": ["dataset:l1.equity_eod"],
                "lookback_sessions": 0,
                "null_policy": "propagate",
                "lifecycle": "experimental",
                "recomputable": True,
            }
        )


def test_dependency_prefix_enforced() -> None:
    with pytest.raises(ValidationError):
        FeatureSpec.model_validate(
            {
                "name": "fw__bad__dep",
                "version": "v1",
                "family": "other",
                "feature_type": "raw",
                "owner": "t",
                "description": "bad dep",
                "dtype": "float",
                "dependencies": ["l1.equity_eod"],
                "lookback_sessions": 0,
                "null_policy": "propagate",
                "lifecycle": "experimental",
                "recomputable": True,
            }
        )


def test_naming_convention() -> None:
    with pytest.raises(ValidationError):
        FeatureSpec.model_validate(
            {
                "name": "BadName",
                "version": "v1",
                "family": "other",
                "feature_type": "raw",
                "owner": "t",
                "description": "bad name",
                "dtype": "float",
                "dependencies": ["dataset:l1.equity_eod"],
                "lookback_sessions": 0,
                "null_policy": "propagate",
                "lifecycle": "experimental",
                "recomputable": True,
            }
        )

```


## FILE: `tests/unit/features/test_dag.py`

```
"""Feature DAG validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from stock_engine.features.dag import validate_dag
from stock_engine.features.registry import load_registry

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "features"


def test_topological_order_parent_before_child() -> None:
    registry = load_registry(FIXTURES / "registry", FIXTURES / "families.yaml")
    dag = validate_dag(registry.all())
    order = dag.topological_order()
    assert order.index("fw__base__panel@v1") < order.index("fw__child__panel@v1")


def test_cycle_rejected() -> None:
    with pytest.raises(ValueError, match="cycle"):
        load_registry(
            FIXTURES / "bad_cycle" / "registry",
            FIXTURES / "bad_cycle" / "families.yaml",
        )

```


## FILE: `tests/unit/features/test_store_publish.py`

```
"""Feature store + publisher framework tests (no feature compute)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from stock_engine.features.publish import FeaturePublishRequest, publish_feature_frame
from stock_engine.features.registry import load_registry
from stock_engine.features.store import LocalParquetFeatureStore

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "features"


def test_local_parquet_roundtrip(tmp_path: Path) -> None:
    store = LocalParquetFeatureStore(tmp_path / "features")
    frame = pd.DataFrame(
        {
            "isin": ["INE001", "INE002"],
            "session_date": ["2026-07-17", "2026-07-17"],
            "fw__base__panel": [1.0, 2.0],
        }
    )
    path = store.write(
        frame,
        feature_set="fixture_set",
        feature_version="v1",
        as_of_date="2026-07-17",
    )
    assert path.exists()
    assert store.exists(feature_set="fixture_set", feature_version="v1", as_of_date="2026-07-17")
    got = store.read(feature_set="fixture_set", feature_version="v1", as_of_date="2026-07-17")
    assert list(got["isin"]) == ["INE001", "INE002"]


def test_publish_writes_manifest(tmp_path: Path) -> None:
    registry = load_registry(FIXTURES / "registry", FIXTURES / "families.yaml")
    frame = pd.DataFrame(
        {
            "isin": ["INE001"],
            "session_date": ["2026-07-17"],
            "fw__base__panel": [0.5],
            "fw__child__panel": [0.25],
        }
    )
    request = FeaturePublishRequest(
        feature_set="fixture_set",
        feature_version="v1",
        as_of_date=date(2026, 7, 17),
        run_id="run-test",
        config_hash="abc",
        config_version="cfg-v1",
        feature_ids=["fw__base__panel@v1", "fw__child__panel@v1"],
        frame=frame,
    )
    manifest = publish_feature_frame(
        request,
        registry,
        features_root=tmp_path / "features",
        metadata_root=tmp_path / "metadata",
    )
    assert manifest.row_count == 1
    assert manifest.registry_hash == registry.registry_hash()
    meta = tmp_path / "metadata" / "features" / "published" / "2026-07-17" / "fixture_set__v1.json"
    assert meta.exists()


def test_production_fail_closed_rejects_nulls(tmp_path: Path) -> None:
    registry = load_registry(
        FIXTURES / "prod" / "registry",
        FIXTURES / "prod" / "families.yaml",
    )
    frame = pd.DataFrame(
        {
            "isin": ["INE001"],
            "session_date": ["2026-07-17"],
            "fw__prod__panel": [None],
        }
    )
    request = FeaturePublishRequest(
        feature_set="prod_set",
        feature_version="v1",
        as_of_date=date(2026, 7, 17),
        run_id="run-test",
        config_hash="abc",
        config_version="cfg-v1",
        feature_ids=["fw__prod__panel@v1"],
        frame=frame,
    )
    with pytest.raises(ValueError, match="nulls not allowed"):
        publish_feature_frame(request, registry, features_root=tmp_path / "features")


def test_production_fail_closed_rejects_out_of_range(tmp_path: Path) -> None:
    registry = load_registry(
        FIXTURES / "prod" / "registry",
        FIXTURES / "prod" / "families.yaml",
    )
    frame = pd.DataFrame(
        {
            "isin": ["INE001"],
            "session_date": ["2026-07-17"],
            "fw__prod__panel": [1.5],
        }
    )
    request = FeaturePublishRequest(
        feature_set="prod_set",
        feature_version="v1",
        as_of_date=date(2026, 7, 17),
        run_id="run-test",
        config_hash="abc",
        config_version="cfg-v1",
        feature_ids=["fw__prod__panel@v1"],
        frame=frame,
    )
    with pytest.raises(ValueError, match="above max_value"):
        publish_feature_frame(request, registry, features_root=tmp_path / "features")

```


## FILE: `tests/unit/features/test_calendar.py`

```
"""Trading-calendar lookback helper tests."""

from __future__ import annotations

from datetime import date

import pytest

from stock_engine.features.calendar import require_lookback_sessions, sessions_on_or_before

CAL = [
    date(2026, 7, 13),
    date(2026, 7, 14),
    date(2026, 7, 15),
    date(2026, 7, 16),
    date(2026, 7, 17),
]


def test_sessions_on_or_before_window() -> None:
    got = sessions_on_or_before(CAL, date(2026, 7, 16), n=3)
    assert [d.date() for d in got] == [
        date(2026, 7, 14),
        date(2026, 7, 15),
        date(2026, 7, 16),
    ]


def test_require_lookback_ok() -> None:
    got = require_lookback_sessions(CAL, date(2026, 7, 17), 5)
    assert len(got) == 5


def test_require_lookback_insufficient() -> None:
    with pytest.raises(ValueError, match="Insufficient trading sessions"):
        require_lookback_sessions(CAL, date(2026, 7, 14), 5)

```

---

## Implementation inventory (honest)

| Criterion | Status in this PR |
|---|---|
| Registry schema (Pydantic) | Yes — `FeatureSpec` |
| Family catalog | Yes — `families.yaml` |
| Registry load + validation | Yes — `load_registry` |
| Circular dependency detection | Yes — DAG topological sort |
| Feature dependency resolution | Partial — feature↔feature DAG yes; dataset deps are declared strings only (not resolved against L1 store yet) |
| Publish pipeline | Yes — validate frame → Parquet → manifest JSON |
| Fail-closed production validation | Yes — finite/min/max/null for `lifecycle=production` |
| Registry hashing | Yes — `registry_hash()` SHA256 of specs |
| Feature / content hashing of Parquet | No — not yet |
| Feature caching | No — store `exists()` only; no cache invalidation layer |
| Incremental recomputation | No — full-frame publish only |
| PIT enforcement in compute | Partial — calendar lookback helpers exist; no compute engine yet to enforce PIT on L1 reads |
| Metadata versioning on publish | Yes — `config_hash`, `config_version`, `registry_hash`, `run_id`, `as_of_date` |
| Reproducibility helpers | Partial — deterministic sort on write; goldens deferred until first production feature |
| Concrete features in `docs/features/registry/` | Empty by design (PICK B) |
