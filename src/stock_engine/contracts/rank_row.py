"""Daily rank-row contract (Phase 1 outputs). No simplex sum requirement."""

from datetime import date

from pydantic import BaseModel, Field


class RankRow(BaseModel):
    """One stock's scored outputs for a single horizon on a single as-of date."""

    symbol: str
    as_of_date: date
    horizon: int = Field(ge=1, description="Trading-day horizon")
    p_bullish: float = Field(ge=0.0, le=1.0)
    p_bearish: float = Field(ge=0.0, le=1.0)
    p_neutral: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional; not required of all models",
    )
    risk: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    rank_long: int = Field(ge=1)
    rank_short: int = Field(ge=1)
    model_version: str
    config_version: str
