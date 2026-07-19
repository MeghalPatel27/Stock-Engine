"""Ingestion package — local CSV → raw → clean Parquet. No external downloaders."""

from stock_engine.ingest.pipeline import IngestResult, run_ingest

__all__ = ["IngestResult", "run_ingest"]
