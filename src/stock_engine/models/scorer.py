"""Production scorer: frozen artifact → RankRow (never reads labels)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.contracts.rank_row import RankRow
from stock_engine.models.artifact import load_artifact
from stock_engine.models.io import load_feature_frame, load_symbol_map_from_l1
from stock_engine.models.ranking import assign_ranks, score_long, score_short
from stock_engine.models.risk_confidence import heuristic_confidence, heuristic_risk
from stock_engine.models.trainer import predict_proba_positive


def score_features_to_rank_rows(
    features: pd.DataFrame,
    *,
    models_root: Path,
    model_name: str,
    model_version: str,
    as_of_date: date,
    horizon: int = 5,
    risk_weight: float = 1.0,
    config_version: str = "0.1.0",
    symbol_by_isin: dict[str, str] | None = None,
    session_date: date | None = None,
) -> list[RankRow]:
    """
    Score a feature panel for one decision session (default: as_of_date).

    Labels must not be present on `features`.
    """
    leak = {"label", "forward_return", "y_bullish", "y_bearish"} & set(features.columns)
    if leak:
        msg = f"inference features must not include label columns: {sorted(leak)}"
        raise ValueError(msg)

    art = load_artifact(models_root, model_name, model_version)
    allow = art["feature_allowlist"]
    missing = [c for c in allow if c not in features.columns]
    if missing:
        msg = f"missing production features: {missing}"
        raise ValueError(msg)

    frame = features.copy()
    frame["isin"] = frame["isin"].astype(str)
    frame["session_date"] = pd.to_datetime(frame["session_date"]).dt.normalize()
    target_session = pd.Timestamp(session_date or as_of_date).normalize()
    panel = frame.loc[frame["session_date"] == target_session].copy()
    if panel.empty:
        msg = f"no feature rows for session {target_session.date()}"
        raise ValueError(msg)
    if panel.duplicated(subset=["isin"]).any():
        msg = "duplicate isin in inference panel"
        raise ValueError(msg)

    X = panel[allow].to_numpy(dtype=float)
    p_bull = predict_proba_positive(art["bullish_model"], X)
    p_bear = predict_proba_positive(art["bearish_model"], X)
    panel = panel.reset_index(drop=True)
    panel["p_bullish"] = p_bull
    panel["p_bearish"] = p_bear
    panel["risk"] = heuristic_risk(panel).to_numpy()
    panel["confidence"] = heuristic_confidence(panel["p_bullish"], panel["p_bearish"]).to_numpy()
    panel["score_long"] = score_long(
        panel["p_bullish"], panel["confidence"], panel["risk"], risk_weight=risk_weight
    )
    panel["score_short"] = score_short(
        panel["p_bearish"], panel["confidence"], panel["risk"], risk_weight=risk_weight
    )
    # Deterministic ranks: sort by score desc, isin asc then first-rank
    panel = panel.sort_values(["score_long", "isin"], ascending=[False, True]).reset_index(
        drop=True
    )
    panel["rank_long"] = assign_ranks(panel["score_long"])
    panel = panel.sort_values(["score_short", "isin"], ascending=[False, True]).reset_index(
        drop=True
    )
    panel["rank_short"] = assign_ranks(panel["score_short"])
    panel = panel.sort_values("isin").reset_index(drop=True)

    sym = symbol_by_isin or {}
    rows: list[RankRow] = []
    for r in panel.itertuples(index=False):
        isin = str(r.isin)
        rows.append(
            RankRow(
                symbol=sym.get(isin, isin),
                as_of_date=as_of_date,
                horizon=horizon,
                p_bullish=float(r.p_bullish),
                p_bearish=float(r.p_bearish),
                p_neutral=None,
                risk=float(r.risk),
                confidence=float(r.confidence),
                rank_long=int(r.rank_long),
                rank_short=int(r.rank_short),
                model_version=model_version,
                config_version=config_version,
            )
        )
    return rows


def score_published_features(
    data_root: Path,
    *,
    as_of_date: date,
    model_name: str,
    model_version: str,
    feature_set: str = "core",
    feature_version: str = "v1",
    risk_weight: float = 1.0,
    config_version: str = "0.1.0",
    horizon: int = 5,
    session_date: date | None = None,
) -> list[RankRow]:
    features = load_feature_frame(
        data_root,
        feature_set=feature_set,
        feature_version=feature_version,
        as_of_date=as_of_date,
    )
    symbol_map = load_symbol_map_from_l1(data_root, as_of_date)
    return score_features_to_rank_rows(
        features,
        models_root=data_root / "models",
        model_name=model_name,
        model_version=model_version,
        as_of_date=as_of_date,
        horizon=horizon,
        risk_weight=risk_weight,
        config_version=config_version,
        symbol_by_isin=symbol_map,
        session_date=session_date,
    )
