"""End-to-end synthetic: train → freeze → score RankRows (no labels at inference)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stock_engine.models.artifact import load_artifact, publish_artifact
from stock_engine.models.scorer import score_features_to_rank_rows
from stock_engine.models.walkforward import fit_final, run_walkforward


def _synthetic_matrix(n_sessions: int = 80, n_names: int = 10) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    sessions = pd.date_range("2024-01-01", periods=n_sessions, freq="B")
    rows = []
    for s in sessions:
        rets = rng.normal(0, 0.02, size=n_names)
        # Feature correlates weakly with future return proxy
        for i in range(n_names):
            rows.append(
                {
                    "isin": f"INE{i:03d}",
                    "session_date": s,
                    "f1": float(rets[i] + rng.normal(0, 0.01)),
                    "f2": float(rng.normal()),
                    "vol__std__20d": float(abs(rng.normal(0.02, 0.005))),
                    "forward_return": float(rets[i]),
                    "label": (
                        "bullish"
                        if rets[i] >= np.quantile(rets, 0.8)
                        else "bearish"
                        if rets[i] <= np.quantile(rets, 0.2)
                        else "neutral"
                    ),
                    "sample_weight": 1.0,
                    "horizon": 5,
                    "y_bullish": int(rets[i] >= np.quantile(rets, 0.8)),
                    "y_bearish": int(rets[i] <= np.quantile(rets, 0.2)),
                }
            )
    return pd.DataFrame(rows)


def test_walkforward_freeze_and_score(tmp_path: Path) -> None:
    matrix = _synthetic_matrix()
    feats = ["f1", "f2", "vol__std__20d"]
    wf = run_walkforward(
        matrix,
        feats,
        horizon=5,
        embargo_sessions=5,
        min_train_sessions=30,
        test_fold_sessions=10,
        step_sessions=10,
        top_k=3,
        risk_weight=0.5,
        model_params={"random_seed": 0, "max_iter": 50, "max_depth": 3, "min_samples_leaf": 5},
    )
    assert wf["summary"]["n_folds"] >= 1
    assert "precision_at_k_long_mean" in wf["summary"]

    bull, bear = fit_final(
        matrix,
        feats,
        model_params={"random_seed": 0, "max_iter": 50, "max_depth": 3, "min_samples_leaf": 5},
    )
    root = tmp_path / "models"
    publish_artifact(
        root,
        model_name="cs_quantile_h5",
        model_version="v1",
        bullish_model=bull,
        bearish_model=bear,
        feature_allowlist=feats,
        train_manifest={"config_hash": "abc", "label_version": "v1", "feature_version": "v1"},
        metrics=wf,
    )
    with pytest.raises(FileExistsError, match="overwrite"):
        publish_artifact(
            root,
            model_name="cs_quantile_h5",
            model_version="v1",
            bullish_model=bull,
            bearish_model=bear,
            feature_allowlist=feats,
            train_manifest={},
            metrics={},
            overwrite=False,
        )

    art = load_artifact(root, "cs_quantile_h5", "v1")
    assert art["feature_allowlist"] == feats

    # Inference panel for last session — features only
    last = matrix["session_date"].max()
    panel = matrix.loc[matrix["session_date"] == last, ["isin", "session_date", *feats]].copy()
    rows = score_features_to_rank_rows(
        panel,
        models_root=root,
        model_name="cs_quantile_h5",
        model_version="v1",
        as_of_date=date(2024, 12, 31),
        session_date=last.date(),
        risk_weight=0.5,
        config_version="0.1.0",
        symbol_by_isin={f"INE{i:03d}": f"SYM{i}" for i in range(10)},
    )
    assert len(rows) == 10
    assert {r.rank_long for r in rows} == set(range(1, 11))
    assert all(0.0 <= r.p_bullish <= 1.0 for r in rows)

    # Labels forbidden at inference
    bad = panel.copy()
    bad["label"] = "bullish"
    with pytest.raises(ValueError, match="label columns"):
        score_features_to_rank_rows(
            bad,
            models_root=root,
            model_name="cs_quantile_h5",
            model_version="v1",
            as_of_date=date(2024, 12, 31),
            session_date=last.date(),
        )
