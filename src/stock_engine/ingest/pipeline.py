"""Ingest pipeline: incoming CSV → raw → DQ → clean Parquet + metadata."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from stock_engine import __version__ as engine_version
from stock_engine.config import load_config_with_hash
from stock_engine.contracts import RunMetadata
from stock_engine.ingest.clean_store import write_clean_parquet
from stock_engine.ingest.datasets import REQUIRED_DATASETS
from stock_engine.ingest.local_csv import LocalIncomingCsvSource
from stock_engine.ingest.manifests import (
    DatasetManifest,
    dq_to_dicts,
    write_dataset_manifest,
    write_pipeline_state,
    write_run_metadata,
)
from stock_engine.ingest.normalize import (
    normalize_corporate_actions,
    normalize_equity_eod,
    normalize_symbol_isin_map,
)
from stock_engine.ingest.protocol import DataArtifact, DataSource
from stock_engine.ingest.raw_store import archive_raw
from stock_engine.ingest.validate import (
    parse_as_of_from_equity,
    validate_corporate_actions,
    validate_equity_eod,
    validate_symbol_isin_map,
    verify_checksum,
)
from stock_engine.logging_utils import bind_pipeline_stage, configure_logging

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    run_id: str
    as_of_date: date
    config_version: str
    config_hash: str
    dataset_version: str
    status: str
    manifests: list[DatasetManifest] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def run_ingest(
    *,
    data_root: Path | None = None,
    as_of_date: date | None = None,
    source: DataSource | None = None,
    dataset_version: str | None = None,
    config_dir: Path | None = None,
) -> IngestResult:
    """
    Execute one ingest run. Fail closed: no clean publish if any required
    dataset fails DQ or is missing.
    """
    cfg, config_version, config_hash = load_config_with_hash(config_dir)
    root = data_root or Path(cfg.get("paths", {}).get("data_root", "data"))
    incoming = root / "incoming"
    raw_root = root / "raw"
    clean_root = root / "clean"
    metadata_root = root / "metadata"

    ds: DataSource = source or LocalIncomingCsvSource(incoming)
    artifacts = ds.list_artifacts(as_of_date=as_of_date)
    by_name = {a.dataset: a for a in artifacts}

    # Infer as_of from equity if not provided
    if "equity_eod" not in by_name:
        run_id = configure_logging(pipeline_stage="ingest")
        result = IngestResult(
            run_id=run_id,
            as_of_date=as_of_date or date.today(),
            config_version=config_version,
            config_hash=config_hash,
            dataset_version=dataset_version or "missing",
            status="failed",
            errors=["missing required dataset: equity_eod"],
        )
        write_pipeline_state(
            metadata_root,
            run_id=run_id,
            as_of_date=result.as_of_date,
            status="failed",
            detail={"errors": result.errors},
        )
        return result

    equity_raw_df = pd.read_csv(by_name["equity_eod"].path)
    equity_raw_df.columns = [str(c).strip().lower() for c in equity_raw_df.columns]
    inferred = as_of_date or parse_as_of_from_equity(equity_raw_df)

    version = dataset_version or f"v{inferred.isoformat().replace('-', '')}"
    run_id = configure_logging(as_of_date=inferred, pipeline_stage="ingest")
    log = bind_pipeline_stage(logger, "ingest")

    meta = RunMetadata(
        run_id=run_id,
        as_of_date=inferred,
        config_hash=config_hash,
        config_version=config_version,
        engine_version=engine_version,
        timestamp=datetime.now(UTC),
    )
    write_run_metadata(meta, metadata_root)
    log.info("ingest start provider=%s datasets=%s", ds.provider_id, sorted(by_name))

    missing_required = REQUIRED_DATASETS - set(by_name)
    errors: list[str] = []
    if missing_required:
        errors.extend(f"missing required dataset: {name}" for name in sorted(missing_required))

    manifests: list[DatasetManifest] = []
    dq_failed = False
    allow_clean = not bool(missing_required)

    processors = {
        "equity_eod": (_process_equity, equity_raw_df),
        "corporate_actions": (_process_corporate_actions, None),
        "symbol_isin_map": (_process_symbol_map, None),
    }

    for dataset, artifact in sorted(by_name.items()):
        if dataset not in processors:
            continue
        try:
            manifest, ok = _ingest_one(
                artifact=artifact,
                preloaded_df=processors[dataset][1] if dataset == "equity_eod" else None,
                processor=processors[dataset][0],
                raw_root=raw_root,
                clean_root=clean_root,
                metadata_root=metadata_root,
                as_of_date=inferred,
                dataset_version=version,
                row_dev=float(cfg.get("ingest", {}).get("row_count_deviation", 0.5)),
                allow_clean_publish=allow_clean,
            )
            manifests.append(manifest)
            if not ok:
                dq_failed = True
                errors.append(f"DQ failed for {dataset}")
        except Exception as exc:  # noqa: BLE001 - fail closed, record error
            dq_failed = True
            errors.append(f"{dataset}: {exc}")
            log.exception("ingest failed for %s", dataset)

    status = "success" if not errors and not dq_failed else "failed"
    # If failed, ensure we did not partially claim success — clean writes only happen on DQ ok
    result = IngestResult(
        run_id=run_id,
        as_of_date=inferred,
        config_version=config_version,
        config_hash=config_hash,
        dataset_version=version,
        status=status,
        manifests=manifests,
        errors=errors,
    )
    write_pipeline_state(
        metadata_root,
        run_id=run_id,
        as_of_date=inferred,
        status=status,
        detail={"errors": errors, "datasets": [m.dataset for m in manifests]},
    )
    log.info("ingest finished status=%s errors=%s", status, errors)
    return result


def _ingest_one(
    *,
    artifact: DataArtifact,
    preloaded_df: pd.DataFrame | None,
    processor,
    raw_root: Path,
    clean_root: Path,
    metadata_root: Path,
    as_of_date: date,
    dataset_version: str,
    row_dev: float,
    allow_clean_publish: bool = True,
) -> tuple[DatasetManifest, bool]:
    raw_path, sidecar = archive_raw(
        artifact,
        raw_root=raw_root,
        as_of_date=as_of_date,
        dataset_version=dataset_version,
    )
    checksum_issue = verify_checksum(raw_path, sidecar.sha256)
    df = preloaded_df if preloaded_df is not None else pd.read_csv(raw_path)
    df.columns = [str(c).strip().lower() for c in df.columns]

    clean_df, report = processor(df, row_dev=row_dev)
    if checksum_issue is not None:
        report.fail(checksum_issue.code, checksum_issue.message)

    clean_path: Path | None = None
    publish_ok = report.ok and allow_clean_publish
    if publish_ok:
        clean_path = write_clean_parquet(
            clean_df,
            clean_root=clean_root,
            dataset=artifact.dataset,
            as_of_date=as_of_date,
            dataset_version=dataset_version,
        )

    manifest = DatasetManifest(
        dataset=artifact.dataset,
        dataset_version=dataset_version,
        as_of_date=as_of_date.isoformat(),
        provider=artifact.provider,
        raw_path=str(raw_path),
        clean_path=str(clean_path) if clean_path else None,
        sha256=sidecar.sha256,
        row_count=report.row_count,
        dq_ok=report.ok,
        dq_issues=dq_to_dicts(report),
    )
    write_dataset_manifest(manifest, metadata_root)
    return manifest, report.ok


def _process_equity(df: pd.DataFrame, *, row_dev: float):
    clean = normalize_equity_eod(df)
    report = validate_equity_eod(clean, row_count_deviation=row_dev)
    return clean, report


def _process_corporate_actions(df: pd.DataFrame, *, row_dev: float):
    clean = normalize_corporate_actions(df)
    report = validate_corporate_actions(clean, row_count_deviation=row_dev)
    return clean, report


def _process_symbol_map(df: pd.DataFrame, *, row_dev: float):
    del row_dev
    clean = normalize_symbol_isin_map(df)
    report = validate_symbol_isin_map(clean)
    return clean, report
