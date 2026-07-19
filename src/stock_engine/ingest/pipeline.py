"""Ingest pipeline: incoming CSV → raw → L0 → (calendar/DQ) → L1."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from stock_engine import __version__ as engine_version
from stock_engine.config import load_config_with_hash
from stock_engine.contracts import RunMetadata
from stock_engine.ingest.adjust import build_l1_equity_eod
from stock_engine.ingest.calendar_checks import detect_missing_sessions
from stock_engine.ingest.clean_store import write_clean_parquet
from stock_engine.ingest.datasets import (
    ADJUSTMENT_METHOD,
    REQUIRED_FOR_L0,
    REQUIRED_FOR_L1,
    SCHEMA_VERSIONS,
)
from stock_engine.ingest.lineage import attach_lineage
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
    normalize_trading_calendar,
)
from stock_engine.ingest.protocol import DataArtifact, DataSource
from stock_engine.ingest.publish_meta import (
    published_meta_for_l1_equity,
    write_published_dataset_meta,
)
from stock_engine.ingest.raw_store import archive_raw
from stock_engine.ingest.validate import (
    parse_as_of_from_equity,
    validate_corporate_actions,
    validate_equity_eod,
    validate_symbol_isin_map,
    validate_trading_calendar,
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
    warnings: list[str] = field(default_factory=list)


def run_ingest(
    *,
    data_root: Path | None = None,
    as_of_date: date | None = None,
    source: DataSource | None = None,
    dataset_version: str | None = None,
    config_dir: Path | None = None,
) -> IngestResult:
    """
    Execute one ingest run.

    - Archives raw (immutable)
    - Publishes L0 on DQ pass for available datasets
    - Publishes L1 equity only when calendar + CA + equity pass and
      missing-session hard checks pass
    """
    cfg, config_version, config_hash = load_config_with_hash(config_dir)
    root = data_root or Path(cfg.get("paths", {}).get("data_root", "data"))
    incoming = root / "incoming"
    raw_root = root / "raw"
    clean_root = root / "clean"
    metadata_root = root / "metadata"

    ingest_cfg = cfg.get("ingest", {})
    lookback_n = int(ingest_cfg.get("missing_session_lookback_n", 5))
    outlier_abs = float(ingest_cfg.get("outlier_abs_return", 0.5))
    row_dev = float(ingest_cfg.get("row_count_deviation", 0.5))

    ds: DataSource = source or LocalIncomingCsvSource(incoming)
    artifacts = ds.list_artifacts(as_of_date=as_of_date)
    by_name = {a.dataset: a for a in artifacts}

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
    ingested_at = datetime.now(UTC)

    meta = RunMetadata(
        run_id=run_id,
        as_of_date=inferred,
        config_hash=config_hash,
        config_version=config_version,
        engine_version=engine_version,
        timestamp=ingested_at,
    )
    write_run_metadata(meta, metadata_root)
    log.info("ingest start provider=%s datasets=%s", ds.provider_id, sorted(by_name))

    errors: list[str] = []
    warnings: list[str] = []
    missing_l0 = REQUIRED_FOR_L0 - set(by_name)
    if missing_l0:
        errors.extend(f"missing required dataset: {name}" for name in sorted(missing_l0))

    manifests: list[DatasetManifest] = []
    l0_frames: dict[str, pd.DataFrame] = {}
    allow_l0 = not bool(missing_l0)

    processors = {
        "equity_eod": (_process_equity, equity_raw_df),
        "corporate_actions": (_process_corporate_actions, None),
        "symbol_isin_map": (_process_symbol_map, None),
        "trading_calendar": (_process_calendar, None),
    }

    for dataset, artifact in sorted(by_name.items()):
        if dataset not in processors:
            continue
        try:
            manifest, ok, frame = _ingest_l0_one(
                artifact=artifact,
                preloaded_df=processors[dataset][1] if dataset == "equity_eod" else None,
                processor=processors[dataset][0],
                raw_root=raw_root,
                clean_root=clean_root,
                metadata_root=metadata_root,
                as_of_date=inferred,
                dataset_version=version,
                row_dev=row_dev,
                allow_clean_publish=allow_l0,
                run_id=run_id,
                ingested_at=ingested_at,
            )
            manifests.append(manifest)
            if ok and frame is not None:
                l0_frames[dataset] = frame
            if not ok:
                errors.append(f"DQ failed for {dataset}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{dataset}: {exc}")
            log.exception("L0 ingest failed for %s", dataset)

    # L1 requires equity + CA + calendar L0 frames
    missing_l1 = REQUIRED_FOR_L1 - set(l0_frames)
    for name in sorted(missing_l1):
        if name not in by_name:
            errors.append(f"missing required dataset for L1: {name}")
        elif f"DQ failed for {name}" not in errors:
            errors.append(f"L1 blocked: {name} unavailable after DQ")

    l1_published = False
    can_build_l1 = (
        allow_l0
        and not missing_l1
        and not any(e.startswith(f"DQ failed for {ds}") for ds in REQUIRED_FOR_L1 for e in errors)
    )

    if can_build_l1:
        miss = detect_missing_sessions(
            l0_frames["equity_eod"],
            l0_frames["trading_calendar"],
            as_of_date=inferred,
            lookback_n=lookback_n,
        )
        for issue in miss.soft_gaps:
            warnings.append(f"{issue.code}: {issue.message}")
        if not miss.ok:
            for issue in miss.hard_gaps:
                errors.append(f"{issue.code}: {issue.message}")
        else:
            l1_df, adj_warnings = build_l1_equity_eod(
                l0_frames["equity_eod"],
                l0_frames["corporate_actions"],
                outlier_abs_return=outlier_abs,
            )
            warnings.extend(adj_warnings)
            eq_art = by_name["equity_eod"]
            eq_manifest = next(m for m in manifests if m.dataset == "equity_eod")
            l1_df = attach_lineage(
                l1_df,
                source_file=eq_art.path.name,
                raw_sha256=eq_manifest.sha256,
                ingested_at=ingested_at,
                provider=eq_art.provider,
                schema_version=SCHEMA_VERSIONS["equity_eod"],
                dataset_version=version,
                run_id=run_id,
            )
            l1_path = write_clean_parquet(
                l1_df,
                clean_root=clean_root,
                tier="l1",
                dataset="equity_eod",
                as_of_date=inferred,
                dataset_version=version,
            )
            for ds_name in ("corporate_actions", "trading_calendar"):
                framed = attach_lineage(
                    l0_frames[ds_name],
                    source_file=by_name[ds_name].path.name,
                    raw_sha256=next(m.sha256 for m in manifests if m.dataset == ds_name),
                    ingested_at=ingested_at,
                    provider=by_name[ds_name].provider,
                    schema_version=SCHEMA_VERSIONS[ds_name],
                    dataset_version=version,
                    run_id=run_id,
                )
                write_clean_parquet(
                    framed,
                    clean_root=clean_root,
                    tier="l1",
                    dataset=ds_name,
                    as_of_date=inferred,
                    dataset_version=version,
                )
            manifests.append(
                DatasetManifest(
                    dataset="equity_eod_l1",
                    dataset_version=version,
                    as_of_date=inferred.isoformat(),
                    provider=eq_art.provider,
                    raw_path=eq_manifest.raw_path,
                    clean_path=str(l1_path),
                    sha256=eq_manifest.sha256,
                    row_count=len(l1_df),
                    dq_ok=True,
                    dq_issues=[],
                )
            )
            write_dataset_manifest(manifests[-1], metadata_root)
            write_published_dataset_meta(
                published_meta_for_l1_equity(
                    schema_version=SCHEMA_VERSIONS["equity_eod"],
                    dataset_version=version,
                    adjustment_method=ADJUSTMENT_METHOD,
                    config_hash=config_hash,
                    config_version=config_version,
                    run_id=run_id,
                    as_of_date=inferred,
                    row_count=len(l1_df),
                    parquet_path=str(l1_path),
                ),
                metadata_root,
            )
            l1_published = True
            log.info("L1 equity published rows=%s path=%s", len(l1_df), l1_path)

    if not l1_published and not errors:
        errors.append("L1 equity_eod was not published")

    status = "success" if not errors else "failed"

    result = IngestResult(
        run_id=run_id,
        as_of_date=inferred,
        config_version=config_version,
        config_hash=config_hash,
        dataset_version=version,
        status=status,
        manifests=manifests,
        errors=errors,
        warnings=warnings,
    )
    write_pipeline_state(
        metadata_root,
        run_id=run_id,
        as_of_date=inferred,
        status=status,
        detail={
            "errors": errors,
            "warnings": warnings,
            "datasets": [m.dataset for m in manifests],
            "config_hash": config_hash,
            "schema_versions": SCHEMA_VERSIONS,
        },
    )
    log.info("ingest finished status=%s errors=%s warnings=%s", status, errors, warnings)
    return result


def _ingest_l0_one(
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
    allow_clean_publish: bool,
    run_id: str,
    ingested_at: datetime,
) -> tuple[DatasetManifest, bool, pd.DataFrame | None]:
    raw_path, sidecar = archive_raw(
        artifact,
        raw_root=raw_root,
        as_of_date=as_of_date,
        dataset_version=dataset_version,
        downloaded_at=ingested_at,
    )
    checksum_issue = verify_checksum(raw_path, sidecar.sha256)
    df = preloaded_df if preloaded_df is not None else pd.read_csv(raw_path)
    df.columns = [str(c).strip().lower() for c in df.columns]

    clean_df, report = processor(df, row_dev=row_dev)
    if checksum_issue is not None:
        report.fail(checksum_issue.code, checksum_issue.message)

    clean_path = None
    published_df = None
    if report.ok and allow_clean_publish:
        lined = attach_lineage(
            clean_df,
            source_file=artifact.path.name,
            raw_sha256=sidecar.sha256,
            ingested_at=ingested_at,
            provider=artifact.provider,
            schema_version=SCHEMA_VERSIONS[artifact.dataset],
            dataset_version=dataset_version,
            run_id=run_id,
        )
        clean_path = write_clean_parquet(
            lined,
            clean_root=clean_root,
            tier="l0",
            dataset=artifact.dataset,
            as_of_date=as_of_date,
            dataset_version=dataset_version,
        )
        published_df = clean_df  # without lineage for internal L1 calc

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
    return manifest, report.ok, published_df if report.ok else None


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


def _process_calendar(df: pd.DataFrame, *, row_dev: float):
    del row_dev
    clean = normalize_trading_calendar(df)
    report = validate_trading_calendar(clean)
    return clean, report
