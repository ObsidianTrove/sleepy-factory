import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import text

import sleepy_factory.artifacts as artifacts
from sleepy_factory.cli import complete_job_stage, orchestrator_tick, run_stage_work, stage_fields
from sleepy_factory.db.models import Job, StageStatus
from sleepy_factory.db.session import SessionLocal

pytestmark = pytest.mark.smoke


def _norm(p: str) -> str:
    return p.replace("\\", "/")


def test_full_pipeline_reaches_done_and_writes_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Keep artifacts isolated per test run.
    monkeypatch.setattr(artifacts, "ARTIFACTS_ROOT", tmp_path / "artifacts", raising=True)

    # If you explicitly run smoke tests, DB should be up. Fail loudly if not.
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))

    # Create a fresh job row for this test.
    with SessionLocal() as db:
        job = Job()
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    try:
        # Move script NEW -> READY (and possibly other jobs too, but we only act on ours below).
        with SessionLocal() as db:
            orchestrator_tick(db)

        # Walk stages and force a deterministic claim/complete cycle for OUR job.
        for stage in ("script", "audio", "visuals", "render"):
            status_field, lease_owner_field, lease_expires_field = stage_fields(stage)
            owner = f"pytest:{os.getpid()}:{stage}"
            now = datetime.now(UTC)

            # Ensure the stage becomes READY for this job.
            with SessionLocal() as db:
                j = db.get(Job, job_id)
                assert j is not None

                if getattr(j, status_field) == StageStatus.NEW:
                    orchestrator_tick(db)
                    db.refresh(j)

                assert getattr(j, status_field) == StageStatus.READY

                # "Claim" only this job (avoid claiming other READY jobs).
                setattr(j, status_field, StageStatus.RUNNING)
                setattr(j, lease_owner_field, owner)
                setattr(j, lease_expires_field, Job.new_lease_expiry(now, minutes=10))
                j.attempts += 1
                db.commit()

            # Produce artifacts for this stage (no DB session held).
            run_stage_work(str(job_id), stage)

            # Complete via the same CAS logic used by workers.
            with SessionLocal() as db:
                ok = complete_job_stage(db, job_id, owner=owner, stage=stage, success=True)
                assert ok is True
                orchestrator_tick(db)

        # Final assertions
        with SessionLocal() as db:
            j = db.get(Job, job_id)
            assert j is not None
            assert j.script_status == StageStatus.DONE
            assert j.audio_status == StageStatus.DONE
            assert j.visuals_status == StageStatus.DONE
            assert j.render_status == StageStatus.DONE

        # Artifacts assertions
        manifest = artifacts.load_manifest(str(job_id))
        kinds = {a["kind"] for a in manifest["artifacts"]}
        relpaths = {_norm(a["relpath"]) for a in manifest["artifacts"]}

        assert {"script_markdown", "audio_wav", "visuals_svg", "render_plan"}.issubset(kinds)

        assert "script/script.md" in relpaths
        assert "audio/audio.wav" in relpaths
        assert "visuals/cover.svg" in relpaths
        assert "render/render_plan.json" in relpaths

        has_mp4 = "final_video" in kinds and "render/final.mp4" in relpaths
        has_txt = "final_output_notice" in kinds and "render/final.txt" in relpaths
        assert has_mp4 or has_txt
    finally:
        # Best-effort cleanup so repeated runs don't bloat the jobs table.
        try:
            with SessionLocal() as db:
                j = db.get(Job, job_id)
                if j is not None:
                    db.delete(j)
                    db.commit()
        except Exception:
            pass
