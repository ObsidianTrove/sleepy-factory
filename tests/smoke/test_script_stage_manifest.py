import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import sleepy_factory.artifacts as artifacts
from sleepy_factory.cli import run_stage_work

pytestmark = pytest.mark.smoke


def _norm(p: str) -> str:
    return p.replace("\\", "/")


def test_stage_work_writes_expected_manifest_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ensure we never write into the real repo artifacts folder during tests.
    monkeypatch.setattr(artifacts, "ARTIFACTS_ROOT", tmp_path / "artifacts", raising=True)

    job_id = "test-job-manifest"

    # Provide a deterministic job spec so script outputs reflect real inputs.
    artifacts.write_job_spec(
        job_id,
        {
            "job_id": job_id,
            "topic": "manifest test topic",
            "format": "short",
            "length_seconds": 60,
            "voice": "calm",
            "created_at": datetime.now(UTC).isoformat(),
        },
    )

    # Run all stages directly (no DB required for this test).
    for stage in ("script", "audio", "visuals", "render"):
        run_stage_work(job_id, stage)

    manifest_path = artifacts.job_dir(job_id) / "manifest.json"
    assert manifest_path.exists(), "manifest.json was not created"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    kinds = {a["kind"] for a in manifest["artifacts"]}
    relpaths = {_norm(a["relpath"]) for a in manifest["artifacts"]}

    # Job spec
    assert "job_spec" in kinds
    assert "job_spec.json" in relpaths

    # Script stage
    assert {"script_markdown", "script_structured"}.issubset(kinds)
    assert "script/script.md" in relpaths
    assert "script/script.json" in relpaths

    # Audio stage
    assert {"audio_wav", "audio_plan"}.issubset(kinds)
    assert "audio/audio.wav" in relpaths
    assert "audio/audio_plan.json" in relpaths

    # Visuals stage
    assert {"visuals_svg", "visuals_plan"}.issubset(kinds)
    assert "visuals/cover.svg" in relpaths
    assert "visuals/visuals_plan.json" in relpaths

    # Render stage (ffmpeg optional)
    assert "render_plan" in kinds
    assert "render/render_plan.json" in relpaths

    has_mp4 = "final_video" in kinds and "render/final.mp4" in relpaths
    has_txt = "final_output_notice" in kinds and "render/final.txt" in relpaths
    assert has_mp4 or has_txt, "Expected either final.mp4 (ffmpeg) or final.txt (no ffmpeg)"

    # Optional sanity: script reflects spec topic.
    script_path = artifacts.job_dir(job_id) / "script" / "script.md"
    if script_path.exists():
        txt = script_path.read_text(encoding="utf-8")
        assert "manifest test topic" in txt
