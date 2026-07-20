"""Build Signal rows from scored RankRows (V1 identity combiner input)."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from stock_engine.contracts.signal import Signal


def signals_from_rank_frame(frame: pd.DataFrame, *, model_version: str) -> list[Signal]:
    """One bullish and one bearish signal per name from head probabilities."""
    ts = datetime.now(tz=UTC)
    out: list[Signal] = []
    for r in frame.itertuples(index=False):
        out.append(
            Signal(
                value=float(r.p_bullish),
                direction="bullish",
                confidence=float(r.confidence),
                timestamp=ts,
                version=f"{model_version}:bullish",
            )
        )
        out.append(
            Signal(
                value=float(r.p_bearish),
                direction="bearish",
                confidence=float(r.confidence),
                timestamp=ts,
                version=f"{model_version}:bearish",
            )
        )
    return out
