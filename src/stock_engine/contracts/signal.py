"""Signal contract (philosophy invariant #1)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Signal(BaseModel):
    """Standardized emission from any rule, statistic, or model."""

    value: float
    direction: Literal["bullish", "bearish", "neutral", "na"]
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime
    version: str
