from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_ROOT = REPO_ROOT / "artifacts"

JOB_SPEC_FILENAME = "job_spec.json"
MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class ArtifactRecord:
    stage: str
    kind: str
    relpath: str
    bytes: int
    sha256: str
    created_at: str  # keep for now; callers may choose deterministic values


def job_dir(job_id: str) -> Path:
    p = ARTIFACTS_ROOT / str(job_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def stage_dir(job_id: str, stage: str) -> Path:
    p = job_dir(job_id) / stage if stage else job_dir(job_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest_path(job_id: str) -> Path:
    return job_dir(job_id) / MANIFEST_FILENAME


def load_manifest(job_id: str) -> dict[str, Any]:
    p = _manifest_path(job_id)
    if not p.exists():
        # Deterministic baseline manifest; timestamps belong in the job spec or per-artifact records.
        return {"job_id": str(job_id), "artifacts": []}
    return json.loads(p.read_text(encoding="utf-8"))


def write_manifest(job_id: str, manifest: dict[str, Any]) -> None:
    job_dir(job_id).mkdir(parents=True, exist_ok=True)
    _manifest_path(job_id).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def append_manifest(job_id: str, record: ArtifactRecord) -> None:
    """
    Keep the manifest stable by de-duping on relpath.
    If a stage is re-run, the newest record replaces the older record for that file.
    """
    manifest = load_manifest(job_id)
    artifacts: list[dict[str, Any]] = list(manifest.get("artifacts", []))

    rec_dict = asdict(record)
    relpath = rec_dict["relpath"]

    replaced = False
    for i, existing in enumerate(artifacts):
        if existing.get("relpath") == relpath:
            artifacts[i] = rec_dict
            replaced = True
            break

    if not replaced:
        artifacts.append(rec_dict)

    manifest["artifacts"] = artifacts
    write_manifest(job_id, manifest)


def write_bytes(job_id: str, stage: str, filename: str, data: bytes, kind: str) -> Path:
    out_dir = stage_dir(job_id, stage)
    p = out_dir / filename
    p.write_bytes(data)

    rec = ArtifactRecord(
        stage=stage,
        kind=kind,
        relpath=p.relative_to(job_dir(job_id)).as_posix(),
        bytes=len(data),
        sha256=_sha256(data),
        # Caller controls determinism here; if you want fully deterministic artifacts,
        # have the caller pass a deterministic created_at in the *content* rather than the manifest.
        created_at="",
    )
    append_manifest(job_id, rec)
    return p


def write_text(job_id: str, stage: str, filename: str, text: str, kind: str) -> Path:
    return write_bytes(job_id, stage, filename, text.encode("utf-8"), kind=kind)


def write_json(job_id: str, stage: str, filename: str, obj: Any, kind: str) -> Path:
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    return write_text(job_id, stage, filename, text, kind=kind)


def write_job_spec(job_id: str, spec: Any) -> Path:
    return write_json(job_id, "", JOB_SPEC_FILENAME, spec, kind="job_spec")


def load_job_spec(job_id: str) -> dict[str, Any] | None:
    p = job_dir(job_id) / JOB_SPEC_FILENAME
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
