"""Quantile cut-size helpers for label assignment."""

from __future__ import annotations

import math
from typing import Literal

SelectionPolicy = Literal["floor", "ceil", "nearest"]


def cut_size(n: int, quantile: float, policy: SelectionPolicy) -> int:
    """Return class size k for population n and quantile under selection_policy."""
    if n < 0:
        msg = "n must be >= 0"
        raise ValueError(msg)
    if not 0.0 <= quantile <= 1.0:
        msg = "quantile must be in [0, 1]"
        raise ValueError(msg)
    if n == 0 or quantile == 0.0:
        return 0
    raw = n * quantile
    if policy == "floor":
        k = int(math.floor(raw))
    elif policy == "ceil":
        k = int(math.ceil(raw))
    elif policy == "nearest":
        k = int(round(raw))
    else:
        msg = f"Unknown selection_policy: {policy}"
        raise ValueError(msg)
    return max(0, min(n, k))


def top_bottom_sizes(
    n: int,
    top_quantile: float,
    bottom_quantile: float,
    policy: SelectionPolicy,
) -> tuple[int, int]:
    """Return (k_top, k_bot) with k_top + k_bot <= n."""
    k_top = cut_size(n, top_quantile, policy)
    k_bot = cut_size(n, bottom_quantile, policy)
    if k_top + k_bot > n:
        k_bot = max(0, n - k_top)
    return k_top, k_bot
