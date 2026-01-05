import json
from pathlib import Path

import pytest

import sleepy_factory.artifacts as artifacts


def _norm(p: str) -> str:
    return p.replace("\\", "/")


def test_artifacts_write_creates_files_and_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Keep artifacts isolated per test run.
    monkeypatch.setattr(artifacts, "ARTIFACTS_ROOT", tmp_path / "artifacts", raising=True)

    job_id = "unit-job-1"

    # Write a few artifacts (no DB required).
    artifacts.write_text(job_id, "script", "script.md", "# Hello\n", kind="script_markdown")
    artifacts.write_json(job_id, "script", "script.json", {"ok": True}, kind="script_structured")

    # Validate manifest exists and is valid JSON.
    manifest_path = artifacts.job_dir(job_id) / "manifest.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["job_id"] == job_id
    assert isinstance(manifest["artifacts"], list)

    kinds = {a["kind"] for a in manifest["artifacts"]}
    relpaths = {_norm(a["relpath"]) for a in manifest["artifacts"]}

    assert "script_markdown" in kinds
    assert "script_structured" in kinds
    assert "script/script.md" in relpaths
    assert "script/script.json" in relpaths

    # Validate files actually exist on disk where relpath claims.
    for a in manifest["artifacts"]:
        rel = Path(a["relpath"])
        full = artifacts.job_dir(job_id) / rel
        assert full.exists()

        # Sanity checks on record fields.
        assert a["bytes"] >= 1
        assert isinstance(a["sha256"], str)
        assert len(a["sha256"]) == 64

    # Dedupe behavior: writing the same relpath again should replace the manifest entry, not append.
    artifacts.write_text(job_id, "script", "script.md", "# Hello again\n", kind="script_markdown")

    manifest2 = json.loads(manifest_path.read_text(encoding="utf-8"))
    relpaths2 = [_norm(a["relpath"]) for a in manifest2["artifacts"]]

    # Only one record for script/script.md
    assert relpaths2.count("script/script.md") == 1

    # Ensure the file content is the new content.
    script_path = artifacts.job_dir(job_id) / Path("script/script.md")
    assert script_path.read_text(encoding="utf-8") == "# Hello again\n"
