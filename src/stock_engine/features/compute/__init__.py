"""Feature compute functions (formulas live here; publisher stays formula-free)."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.compute.cs import (
    compute_cs_rank_mom_ret_5d,
    compute_cs_zscore_liq_adv_20d,
    compute_cs_zscore_mom_ret_5d,
    compute_cs_zscore_mom_ret_20d,
    compute_cs_zscore_trend_price_vs_ema_20,
    compute_cs_zscore_vol_std_20d,
)
from stock_engine.features.compute.indicators import (
    compute_trend_macd_12_26_9,
    compute_trend_macd_hist_12_26_9,
    compute_trend_macd_signal_12_26_9,
    compute_trend_rsi_14,
)
from stock_engine.features.compute.liq import compute_liq_adv_20d, compute_liq_adv_60d
from stock_engine.features.compute.mom_ret import (
    compute_mom_ret_1d,
    compute_mom_ret_5d,
    compute_mom_ret_20d,
    compute_mom_ret_60d,
)
from stock_engine.features.compute.raw_close_adj import (
    compute_raw_close_adj_l1,
    compute_raw_traded_value_l1,
    compute_raw_volume_adj_l1,
)
from stock_engine.features.compute.trend import (
    compute_trend_ema_10,
    compute_trend_ema_20,
    compute_trend_ema_50,
    compute_trend_ema_spread_10_50,
    compute_trend_price_vs_ema_20,
    compute_trend_slope_ema20_5d,
    compute_trend_sma_20,
    compute_trend_sma_50,
)
from stock_engine.features.compute.vol import compute_vol_std_20d, compute_vol_std_60d
from stock_engine.features.models import FeatureSpec

FeatureComputer = Callable[[ComputeContext, FeatureSpec], pd.DataFrame]

FEATURE_COMPUTERS: dict[str, FeatureComputer] = {
    "raw__close_adj__l1@v1": compute_raw_close_adj_l1,
    "raw__volume_adj__l1@v1": compute_raw_volume_adj_l1,
    "raw__traded_value__l1@v1": compute_raw_traded_value_l1,
    "mom__ret__1d@v1": compute_mom_ret_1d,
    "mom__ret__5d@v1": compute_mom_ret_5d,
    "mom__ret__20d@v1": compute_mom_ret_20d,
    "mom__ret__60d@v1": compute_mom_ret_60d,
    "trend__ema__10@v1": compute_trend_ema_10,
    "trend__ema__20@v1": compute_trend_ema_20,
    "trend__ema__50@v1": compute_trend_ema_50,
    "trend__sma__20@v1": compute_trend_sma_20,
    "trend__sma__50@v1": compute_trend_sma_50,
    "trend__price_vs_ema__20@v1": compute_trend_price_vs_ema_20,
    "trend__ema_spread__10_50@v1": compute_trend_ema_spread_10_50,
    "trend__slope__ema20__5d@v1": compute_trend_slope_ema20_5d,
    "trend__rsi__14@v1": compute_trend_rsi_14,
    "trend__macd__12_26_9@v1": compute_trend_macd_12_26_9,
    "trend__macd_signal__12_26_9@v1": compute_trend_macd_signal_12_26_9,
    "trend__macd_hist__12_26_9@v1": compute_trend_macd_hist_12_26_9,
    "vol__std__20d@v1": compute_vol_std_20d,
    "vol__std__60d@v1": compute_vol_std_60d,
    "liq__adv__20d@v1": compute_liq_adv_20d,
    "liq__adv__60d@v1": compute_liq_adv_60d,
    "cs__zscore__mom__ret__5d@v1": compute_cs_zscore_mom_ret_5d,
    "cs__zscore__mom__ret__20d@v1": compute_cs_zscore_mom_ret_20d,
    "cs__rank__mom__ret__5d@v1": compute_cs_rank_mom_ret_5d,
    "cs__zscore__vol__std__20d@v1": compute_cs_zscore_vol_std_20d,
    "cs__zscore__liq__adv__20d@v1": compute_cs_zscore_liq_adv_20d,
    "cs__zscore__trend__price_vs_ema__20@v1": compute_cs_zscore_trend_price_vs_ema_20,
}


def get_computer(feature_id: str) -> FeatureComputer:
    if feature_id not in FEATURE_COMPUTERS:
        msg = f"No computer registered for {feature_id}"
        raise KeyError(msg)
    return FEATURE_COMPUTERS[feature_id]


def compute_feature(
    feature_id: str,
    *,
    ctx: ComputeContext,
    spec: FeatureSpec,
) -> pd.DataFrame:
    return get_computer(feature_id)(ctx, spec)
