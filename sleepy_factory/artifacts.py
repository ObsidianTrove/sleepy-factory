from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_ROOT = REPO_ROOT / "artifacts"


@dataclass(frozen=True)
class ArtifactRecord:
    stage: str
    kind: str
    relpath: str
    bytes: int
    sha256: str
    created_at: str


def job_dir(job_id: str) -> Path:
    p = ARTIFACTS_ROOT / str(job_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def stage_dir(job_id: str, stage: str) -> Path:
    p = job_dir(job_id) / stage
    p.mkdir(parents=True, exist_ok=True)
    return p


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest_path(job_id: str) -> Path:
    return job_dir(job_id) / "manifest.json"


def load_manifest(job_id: str) -> dict[str, Any]:
    p = _manifest_path(job_id)
    if not p.exists():
        return {
            "job_id": str(job_id),
            "created_at": datetime.now(UTC).isoformat(),
            "artifacts": [],
        }
    return json.loads(p.read_text(encoding="utf-8"))


def write_manifest(job_id: str, manifest: dict[str, Any]) -> None:
    job_dir(job_id).mkdir(parents=True, exist_ok=True)
    _manifest_path(job_id).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def append_manifest(job_id: str, record: ArtifactRecord) -> None:
    manifest = load_manifest(job_id)
    manifest["artifacts"].append(asdict(record))
    write_manifest(job_id, manifest)


def write_bytes(job_id: str, stage: str, filename: str, data: bytes, kind: str) -> Path:
    out_dir = stage_dir(job_id, stage)
    p = out_dir / filename
    p.write_bytes(data)

    rec = ArtifactRecord(
        stage=stage,
        kind=kind,
        relpath=str(p.relative_to(job_dir(job_id))),
        bytes=len(data),
        sha256=_sha256(data),
        created_at=datetime.now(UTC).isoformat(),
    )
    append_manifest(job_id, rec)
    return p


def write_text(job_id: str, stage: str, filename: str, text: str, kind: str) -> Path:
    return write_bytes(job_id, stage, filename, text.encode("utf-8"), kind=kind)


def write_json(job_id: str, stage: str, filename: str, obj: Any, kind: str) -> Path:
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    return write_text(job_id, stage, filename, text, kind=kind)
