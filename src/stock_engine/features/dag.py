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
