"""Production scorer: frozen artifact → RankRow (never reads labels)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.contracts.rank_row import RankRow
from stock_engine.models.artifact import is_per_stock_bundle, load_artifact, load_bundle_manifest
from stock_engine.models.io import load_feature_frame, load_symbol_map_from_l1
from stock_engine.models.ranking import assign_ranks
from stock_engine.models.score_row import score_row


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

    art = (
        load_artifact(models_root, model_name, model_version)
        if not is_per_stock_bundle(models_root, model_name, model_version)
        else None
    )
    if art is not None:
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

    per_stock = is_per_stock_bundle(models_root, model_name, model_version)
    if per_stock:
        bundle = load_bundle_manifest(models_root, model_name, model_version)
        allowed_isins = set(bundle.get("isins", []))
        scores: list[dict[str, float]] = []
        for _, row in panel.iterrows():
            isin = str(row["isin"])
            if allowed_isins and isin not in allowed_isins:
                msg = f"no per-stock model for isin={isin}"
                raise ValueError(msg)
            art = load_artifact(models_root, model_name, model_version, isin=isin)
            allow = art["feature_allowlist"]
            missing = [c for c in allow if c not in panel.columns]
            if missing:
                msg = f"missing features for {isin}: {missing}"
                raise ValueError(msg)
            scores.append(score_row(row, allow, art, risk_weight=risk_weight))
        panel = panel.reset_index(drop=True)
        for key in ("p_bullish", "p_bearish", "risk", "confidence", "score_long", "score_short"):
            panel[key] = [s[key] for s in scores]
    else:
        art = load_artifact(models_root, model_name, model_version)
        allow = art["feature_allowlist"]
        missing = [c for c in allow if c not in features.columns]
        if missing:
            msg = f"missing production features: {missing}"
            raise ValueError(msg)
        panel = panel.reset_index(drop=True)
        row_scores = [
            score_row(panel.loc[i], allow, art, risk_weight=risk_weight) for i in range(len(panel))
        ]
        for key in ("p_bullish", "p_bearish", "risk", "confidence", "score_long", "score_short"):
            panel[key] = [s[key] for s in row_scores]

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
