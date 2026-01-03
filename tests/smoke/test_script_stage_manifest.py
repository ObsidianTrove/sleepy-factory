import json
from pathlib import Path

import pytest

try:
    import sleepy_factory.artifacts as artifacts
    from sleepy_factory.cli import run_stage_work  # imports DB config too
except Exception as exc:  # pragma: no cover
    pytest.skip(str(exc), allow_module_level=True)


def test_script_stage_writes_manifest_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ensure we never write into the real repo artifacts folder during tests.
    monkeypatch.setattr(artifacts, "ARTIFACTS_ROOT", tmp_path / "artifacts")

    job_id = "test-job-script-manifest"

    run_stage_work(job_id, "script")

    manifest_path = artifacts.job_dir(job_id) / "manifest.json"
    assert manifest_path.exists(), "manifest.json was not created"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    kinds = {a["kind"] for a in manifest["artifacts"]}
    relpaths = {a["relpath"] for a in manifest["artifacts"]}

    assert "script_markdown" in kinds
    assert "script_structured" in kinds

    assert "script/script.md" in relpaths
    assert "script/script.json" in relpaths
