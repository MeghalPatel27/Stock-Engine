"""Build train matrix: features(T) ⋈ labels(T, H)."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

KEY = ["isin", "session_date"]
LABEL_KEEP = [
    "label",
    "forward_return",
    "sample_weight",
    "horizon",
    "label_version",
    "universe_mode",
    "label_source",
]


def build_train_matrix(
    features: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    feature_columns: Iterable[str] | None = None,
    horizon: int = 5,
) -> pd.DataFrame:
    """
    Inner-join features and labels on (isin, session_date).

    Rejects empty result, duplicate keys, horizon mismatch, and label columns
    leaking into the feature side.
    """
    if features.empty:
        msg = "empty feature frame"
        raise ValueError(msg)
    if labels.empty:
        msg = "empty label frame"
        raise ValueError(msg)

    feat = features.copy()
    lab = labels.copy()
    feat["isin"] = feat["isin"].astype(str)
    lab["isin"] = lab["isin"].astype(str)
    feat["session_date"] = pd.to_datetime(feat["session_date"]).dt.normalize()
    lab["session_date"] = pd.to_datetime(lab["session_date"]).dt.normalize()

    if feat.duplicated(subset=KEY).any():
        msg = "duplicate feature keys (isin, session_date)"
        raise ValueError(msg)
    if lab.duplicated(subset=KEY).any():
        msg = "duplicate label keys (isin, session_date)"
        raise ValueError(msg)

    if "horizon" in lab.columns and not (lab["horizon"] == horizon).all():
        msg = f"label horizon must be {horizon}"
        raise ValueError(msg)

    forbidden = {"label", "forward_return", "y_bullish", "y_bearish"}
    leak = forbidden & set(feat.columns)
    if leak:
        msg = f"feature frame must not contain label columns: {sorted(leak)}"
        raise ValueError(msg)

    if feature_columns is None:
        feature_columns = [c for c in feat.columns if c not in KEY]
    feature_columns = list(feature_columns)
    if not feature_columns:
        msg = "no feature columns selected"
        raise ValueError(msg)
    dup_feats = pd.Index(feature_columns)[pd.Index(feature_columns).duplicated()].tolist()
    if dup_feats:
        msg = f"duplicate feature IDs in allow-list: {dup_feats}"
        raise ValueError(msg)
    missing = [c for c in feature_columns if c not in feat.columns]
    if missing:
        msg = f"missing feature columns: {missing}"
        raise ValueError(msg)

    keep_lab = [c for c in LABEL_KEEP if c in lab.columns]
    merged = feat[KEY + feature_columns].merge(
        lab[KEY + keep_lab],
        on=KEY,
        how="inner",
        validate="one_to_one",
    )
    if merged.empty:
        msg = "empty training matrix after features ⋈ labels"
        raise ValueError(msg)

    merged["y_bullish"] = (merged["label"] == "bullish").astype(int)
    merged["y_bearish"] = (merged["label"] == "bearish").astype(int)
    if "sample_weight" not in merged.columns:
        merged["sample_weight"] = 1.0
    return merged.sort_values(KEY).reset_index(drop=True)
