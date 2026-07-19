"""Unit tests for logging bootstrap."""

import logging
from datetime import date

from stock_engine.logging_utils import RunContextFilter, configure_logging, new_run_id


def test_new_run_id_unique() -> None:
    assert new_run_id() != new_run_id()


def test_configure_logging_returns_run_id() -> None:
    rid = configure_logging(as_of_date=date(2026, 7, 18), pipeline_stage="bootstrap")
    assert rid
    logging.getLogger("test").info("hello")


def test_run_context_filter_sets_attributes() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    filt = RunContextFilter("rid-1", as_of_date=date(2026, 7, 18), pipeline_stage="ingest")
    assert filt.filter(record) is True
    assert record.run_id == "rid-1"  # type: ignore[attr-defined]
    assert record.as_of_date == "2026-07-18"  # type: ignore[attr-defined]
    assert record.pipeline_stage == "ingest"  # type: ignore[attr-defined]
