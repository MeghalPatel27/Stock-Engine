"""Logging bootstrap with run context (run_id, as_of_date, pipeline_stage)."""

from __future__ import annotations

import logging
import uuid
from datetime import date


class RunContextFilter(logging.Filter):
    """Inject run fields onto every log record."""

    def __init__(
        self,
        run_id: str,
        as_of_date: date | None = None,
        pipeline_stage: str | None = None,
    ) -> None:
        super().__init__()
        self.run_id = run_id
        self.as_of_date = as_of_date.isoformat() if as_of_date else "-"
        self.pipeline_stage = pipeline_stage or "-"

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self.run_id  # type: ignore[attr-defined]
        record.as_of_date = self.as_of_date  # type: ignore[attr-defined]
        record.pipeline_stage = getattr(record, "pipeline_stage", self.pipeline_stage)
        return True


LOG_FORMAT = (
    "%(asctime)s %(levelname)s run_id=%(run_id)s as_of_date=%(as_of_date)s "
    "pipeline_stage=%(pipeline_stage)s %(name)s: %(message)s"
)


def new_run_id() -> str:
    return str(uuid.uuid4())


def configure_logging(
    *,
    run_id: str | None = None,
    as_of_date: date | None = None,
    pipeline_stage: str | None = None,
    level: int = logging.INFO,
) -> str:
    """
    Configure root logging for one execution.

    Returns the run_id used.
    """
    rid = run_id or new_run_id()
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.addFilter(RunContextFilter(rid, as_of_date=as_of_date, pipeline_stage=pipeline_stage))
    root.addHandler(handler)
    return rid


def bind_pipeline_stage(
    logger: logging.Logger, stage: str
) -> logging.LoggerAdapter[logging.Logger]:
    """Return an adapter that sets pipeline_stage on each log call."""
    return logging.LoggerAdapter(logger, {"pipeline_stage": stage})
