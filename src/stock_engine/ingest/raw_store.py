"""Immutable raw archive with SHA-256 sidecars."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from stock_engine.ingest.protocol import DataArtifact


@dataclass(frozen=True)
class RawSidecar:
    sha256: str
    downloaded_at: str
    session_date: str | None
    as_of_date: str
    provider: str
    dataset: str
    dataset_version: str
    original_filename: str
    byte_size: int


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def archive_raw(
    artifact: DataArtifact,
    *,
    raw_root: Path,
    as_of_date: date,
    dataset_version: str,
    downloaded_at: datetime | None = None,
) -> tuple[Path, RawSidecar]:
    """
    Copy artifact into raw store. Never overwrite an existing identical path;
    if path exists with different checksum, write a new versioned filename.
    """
    ts = downloaded_at or datetime.now(UTC)
    digest = sha256_file(artifact.path)
    session = artifact.session_date or as_of_date

    dest_dir = raw_root / artifact.provider / artifact.dataset / as_of_date.isoformat()
    dest_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"{artifact.dataset}__{session.isoformat()}__{digest[:12]}.csv"
    dest = dest_dir / base_name
    sidecar_path = dest.with_suffix(dest.suffix + ".sha256.json")

    if dest.exists():
        existing = sha256_file(dest)
        if existing != digest:
            msg = f"Raw path exists with different checksum: {dest}"
            raise FileExistsError(msg)
        # identical — reuse
    else:
        shutil.copy2(artifact.path, dest)

    sidecar = RawSidecar(
        sha256=digest,
        downloaded_at=ts.isoformat(),
        session_date=session.isoformat(),
        as_of_date=as_of_date.isoformat(),
        provider=artifact.provider,
        dataset=artifact.dataset,
        dataset_version=dataset_version,
        original_filename=artifact.path.name,
        byte_size=dest.stat().st_size,
    )
    sidecar_path.write_text(json.dumps(asdict(sidecar), indent=2) + "\n", encoding="utf-8")
    return dest, sidecar
