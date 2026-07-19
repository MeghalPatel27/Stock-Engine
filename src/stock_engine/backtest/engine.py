"""Purged walk-forward paper backtest on published real data only."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from stock_engine.backtest.costs import (
    DeliveryCostModel,
    round_trip_variable_fraction,
    trade_cost_inr,
)
from stock_engine.backtest.metrics import summarize_returns
from stock_engine.backtest.prices import holding_period_return, load_l1_price_panel
from stock_engine.models.io import load_train_matrix
from stock_engine.models.purge import build_expanding_folds, mask_test_fold, mask_train_fold
from stock_engine.models.ranking import score_long, score_short
from stock_engine.models.risk_confidence import heuristic_confidence, heuristic_risk
from stock_engine.models.trainer import fit_two_heads, predict_proba_positive


@dataclass
class BacktestResult:
    status: str
    as_of_date: date
    metrics: dict[str, float] = field(default_factory=dict)
    fold_metrics: list[dict[str, Any]] = field(default_factory=list)
    trades: pd.DataFrame | None = None
    period_returns: pd.DataFrame | None = None
    errors: list[str] = field(default_factory=list)
    cost_model: dict[str, Any] = field(default_factory=dict)


def _feature_columns(matrix: pd.DataFrame) -> list[str]:
    skip = {
        "isin",
        "session_date",
        "label",
        "forward_return",
        "sample_weight",
        "horizon",
        "label_version",
        "universe_mode",
        "label_source",
        "y_bullish",
        "y_bearish",
    }
    cols = [c for c in matrix.columns if c not in skip]
    if not cols:
        raise ValueError("no feature columns in train matrix")
    return cols


def _score_panel(
    panel: pd.DataFrame,
    feature_columns: list[str],
    bull: Any,
    bear: Any,
    *,
    risk_weight: float,
) -> pd.DataFrame:
    X = panel[feature_columns].to_numpy(dtype=float)
    out = panel.copy()
    out["p_bullish"] = predict_proba_positive(bull, X)
    out["p_bearish"] = predict_proba_positive(bear, X)
    out["risk"] = heuristic_risk(out).to_numpy()
    out["confidence"] = heuristic_confidence(out["p_bullish"], out["p_bearish"]).to_numpy()
    out["score_long"] = score_long(
        out["p_bullish"], out["confidence"], out["risk"], risk_weight=risk_weight
    )
    out["score_short"] = score_short(
        out["p_bearish"], out["confidence"], out["risk"], risk_weight=risk_weight
    )
    return out


def _pick_legs(scored: pd.DataFrame, *, top_k: int) -> tuple[list[str], list[str]]:
    n = len(scored)
    k = min(top_k, max(1, n // 2))
    longs = (
        scored.sort_values(["score_long", "isin"], ascending=[False, True])
        .head(k)["isin"]
        .astype(str)
        .tolist()
    )
    shorts = (
        scored.sort_values(["score_short", "isin"], ascending=[False, True])
        .head(k)["isin"]
        .astype(str)
        .tolist()
    )
    # Avoid the same name on both sides; prefer long if conflict
    shorts = [s for s in shorts if s not in set(longs)]
    if not shorts and n > k:
        remain = scored.loc[~scored["isin"].astype(str).isin(longs)]
        shorts = (
            remain.sort_values(["score_short", "isin"], ascending=[False, True])
            .head(k)["isin"]
            .astype(str)
            .tolist()
        )
    return longs, shorts


def run_walkforward_backtest(
    *,
    data_root: Path,
    as_of_date: date,
    horizon: int = 5,
    top_k: int = 20,
    risk_weight: float = 1.0,
    capital_inr: float = 1_000_000.0,
    cost_model: DeliveryCostModel | None = None,
    modeling_cfg: dict[str, Any] | None = None,
    feature_set: str = "core",
    feature_version: str = "v1",
    label_set: str = "core",
    label_version: str = "v1",
) -> BacktestResult:
    """
    Run purged expanding WF paper backtest on published partitions only.

    Gross leg return: open(T+1) → open(T+1+H) from L1 adjusted prices.
    Net: subtract delivery cost model on entry+exit notionals.
    """
    errors: list[str] = []
    costs = cost_model or DeliveryCostModel()
    mcfg = modeling_cfg or {}

    try:
        prices, sessions = load_l1_price_panel(data_root, as_of_date)
        matrix = load_train_matrix(
            data_root,
            as_of_date=as_of_date,
            feature_set=feature_set,
            feature_version=feature_version,
            label_set=label_set,
            label_version=label_version,
            horizon=horizon,
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        return BacktestResult(
            status="failed",
            as_of_date=as_of_date,
            errors=[str(exc)],
            cost_model=costs.__dict__,
        )

    # Refuse tiny/non-real panels: require multi-year history
    n_sessions = int(matrix["session_date"].nunique())
    if n_sessions < int(mcfg.get("min_train_sessions", 60)) + horizon + 21:
        errors.append(f"insufficient real history for WF backtest: n_sessions={n_sessions}")
        return BacktestResult(
            status="failed",
            as_of_date=as_of_date,
            errors=errors,
            cost_model=costs.__dict__,
        )

    feature_columns = _feature_columns(matrix)
    folds = build_expanding_folds(
        pd.DatetimeIndex(matrix["session_date"].unique()),
        horizon=horizon,
        embargo_sessions=int(mcfg.get("embargo_sessions", horizon)),
        min_train_sessions=int(mcfg.get("min_train_sessions", 60)),
        test_fold_sessions=int(mcfg.get("test_fold_sessions", 21)),
        step_sessions=int(mcfg.get("step_sessions", 21)),
    )
    if not folds:
        return BacktestResult(
            status="failed",
            as_of_date=as_of_date,
            errors=["no walk-forward folds produced from real sessions"],
            cost_model=costs.__dict__,
        )

    trade_rows: list[dict[str, Any]] = []
    period_rows: list[dict[str, Any]] = []
    fold_metrics: list[dict[str, Any]] = []
    model_params = {
        "learning_rate": mcfg.get("learning_rate", 0.05),
        "max_depth": mcfg.get("max_depth", 4),
        "max_leaf_nodes": mcfg.get("max_leaf_nodes", 31),
        "min_samples_leaf": mcfg.get("min_samples_leaf", 20),
        "l2_regularization": mcfg.get("l2_regularization", 1.0),
        "random_seed": mcfg.get("random_seed", 42),
        "max_iter": mcfg.get("max_iter", 100),
    }

    # Non-overlapping decisions inside each fold: every `horizon` sessions
    for fold in folds:
        train = matrix.loc[mask_train_fold(matrix["session_date"], fold)]
        test = matrix.loc[mask_test_fold(matrix["session_date"], fold)]
        if train.empty or test.empty:
            continue
        bull, bear = fit_two_heads(train, feature_columns, params=model_params)

        test_sessions = sorted(pd.to_datetime(test["session_date"]).dt.normalize().unique())
        # Sample decision days every H sessions within fold
        decision_sessions = test_sessions[::horizon]
        fold_period_rets: list[float] = []

        for decision in decision_sessions:
            day = test.loc[pd.to_datetime(test["session_date"]).dt.normalize() == decision]
            if day.empty:
                continue
            scored = _score_panel(day, feature_columns, bull, bear, risk_weight=risk_weight)
            longs, shorts = _pick_legs(scored, top_k=top_k)
            if not longs or not shorts:
                continue

            long_w = 0.5 / len(longs)
            short_w = 0.5 / len(shorts)
            gross = 0.0
            cost_frac_book = 0.0
            legs_ok = True
            for isin in longs:
                ret = holding_period_return(
                    prices, sessions, isin=isin, decision_session=decision, horizon=horizon
                )
                if ret is None:
                    legs_ok = False
                    break
                notional = capital_inr * long_w
                c_buy = trade_cost_inr(side="buy", notional_inr=notional, model=costs)
                c_sell = trade_cost_inr(side="sell", notional_inr=notional, model=costs)
                # Net contribution: weight * gross - costs/capital
                gross += long_w * ret
                cost_frac_book += (c_buy + c_sell) / capital_inr
                trade_rows.append(
                    {
                        "fold_id": fold.fold_id,
                        "decision_session": decision,
                        "isin": isin,
                        "side": "long",
                        "weight": long_w,
                        "gross_return": ret,
                        "cost_inr": c_buy + c_sell,
                    }
                )
            if not legs_ok:
                continue
            for isin in shorts:
                ret = holding_period_return(
                    prices, sessions, isin=isin, decision_session=decision, horizon=horizon
                )
                if ret is None:
                    legs_ok = False
                    break
                notional = capital_inr * short_w
                # Short: sell then buy-to-cover — use sell then buy cost schedule
                c_sell = trade_cost_inr(side="sell", notional_inr=notional, model=costs)
                c_buy = trade_cost_inr(side="buy", notional_inr=notional, model=costs)
                gross += short_w * (-ret)  # profit when price falls
                cost_frac_book += (c_buy + c_sell) / capital_inr
                trade_rows.append(
                    {
                        "fold_id": fold.fold_id,
                        "decision_session": decision,
                        "isin": isin,
                        "side": "short",
                        "weight": short_w,
                        "gross_return": -ret,
                        "cost_inr": c_buy + c_sell,
                    }
                )
            if not legs_ok:
                continue

            net = gross - cost_frac_book
            fold_period_rets.append(net)
            period_rows.append(
                {
                    "fold_id": fold.fold_id,
                    "decision_session": decision,
                    "gross_return": gross,
                    "cost_fraction": cost_frac_book,
                    "net_return": net,
                    "n_long": len(longs),
                    "n_short": len(shorts),
                }
            )

        if fold_period_rets:
            sm = summarize_returns(
                pd.Series(fold_period_rets),
                periods_per_year=252.0 / float(horizon),
            )
            sm["fold_id"] = float(fold.fold_id)
            fold_metrics.append(sm)

    if not period_rows:
        return BacktestResult(
            status="failed",
            as_of_date=as_of_date,
            errors=["no completed paper periods (check fills / folds)"],
            cost_model=costs.__dict__,
            fold_metrics=fold_metrics,
        )

    periods = pd.DataFrame(period_rows)
    trades = pd.DataFrame(trade_rows)
    overall = summarize_returns(
        periods["net_return"],
        periods_per_year=252.0 / float(horizon),
    )
    overall["mean_gross_return"] = float(periods["gross_return"].mean())
    overall["mean_cost_fraction"] = float(periods["cost_fraction"].mean())
    overall["round_trip_variable_frac"] = float(round_trip_variable_fraction(costs))
    overall["n_trades"] = float(len(trades))
    overall["n_folds_used"] = float(len(fold_metrics))
    overall["universe_n_isins"] = float(matrix["isin"].nunique())
    overall["history_sessions"] = float(n_sessions)

    return BacktestResult(
        status="success",
        as_of_date=as_of_date,
        metrics=overall,
        fold_metrics=fold_metrics,
        trades=trades,
        period_returns=periods,
        errors=errors,
        cost_model=costs.__dict__,
    )
