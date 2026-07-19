"""Run metadata persisted for every engine execution."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class RunMetadata(BaseModel):
    """Identity and reproducibility fingerprint for one pipeline run."""

    run_id: str = Field(min_length=1)
    as_of_date: date
    config_hash: str = Field(min_length=1)
    config_version: str = Field(min_length=1)
    engine_version: str = Field(min_length=1)
    timestamp: datetime
