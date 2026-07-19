"""Raw L1 projections."""

from __future__ import annotations

from stock_engine.features.compute.common import project_l1_column
from stock_engine.features.compute.context import ComputeContext
from stock_engine.features.models import FeatureSpec


def compute_raw_close_adj_l1(ctx: ComputeContext, spec: FeatureSpec):
    return project_l1_column(ctx, spec, source_col="close_adj", require_positive=True)


def compute_raw_volume_adj_l1(ctx: ComputeContext, spec: FeatureSpec):
    return project_l1_column(ctx, spec, source_col="volume_adj", require_positive=True)


def compute_raw_traded_value_l1(ctx: ComputeContext, spec: FeatureSpec):
    return project_l1_column(ctx, spec, source_col="traded_value", require_positive=True)
