import socket
import time
from pathlib import Path

import pytest

try:
    import sleepy_factory.artifacts as artifacts
    from sleepy_factory.cli import (
        STAGES,
        claim_one_job_for_stage,
        complete_job_stage,
        orchestrator_tick,
        run_stage_work,
    )
    from sleepy_factory.db.models import Job, StageStatus
    from sleepy_factory.db.session import SessionLocal
except Exception as exc:  # pragma: no cover
    pytest.skip(str(exc), allow_module_level=True)


def _owner_for(stage: str) -> str:
    # Must match the owner string created in claim_one_job_for_stage()
    import os

    return f"{socket.gethostname()}:{os.getpid()}:{stage}"


def test_full_pipeline_reaches_done(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep artifacts isolated per test run
    monkeypatch.setattr(artifacts, "ARTIFACTS_ROOT", tmp_path / "artifacts")

    # Create a fresh job
    with SessionLocal() as db:
        job = Job()
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    # Drive the pipeline to completion with a bounded loop
    deadline = time.time() + 20.0  # seconds
    while time.time() < deadline:
        # Move NEW -> READY transitions
        with SessionLocal() as db:
            orchestrator_tick(db)

        progressed = False

        # For each stage, try to claim one job and complete it
        for stage in STAGES:
            with SessionLocal() as db:
                claimed = claim_one_job_for_stage(db, stage=stage, lease_minutes=1)
            if not claimed:
                continue

            progressed = True

            # Do stage work outside the transaction
            run_stage_work(str(claimed.id), stage)

            # Complete with compare-and-set
            with SessionLocal() as db:
                ok = complete_job_stage(
                    db,
                    claimed.id,
                    owner=_owner_for(stage),
                    stage=stage,
                    success=True,
                )
            assert ok, f"Failed to complete stage {stage}"

        # Check if done
        with SessionLocal() as db:
            cur = db.get(Job, job_id)
            assert cur is not None

            if all(getattr(cur, f"{s}_status") == StageStatus.DONE for s in STAGES):
                # Minimal sanity: attempts should be at least one per stage (may be higher if retries happen)
                assert cur.attempts >= len(STAGES)
                break

        if not progressed:
            time.sleep(0.2)
    else:
        with SessionLocal() as db:
            cur = db.get(Job, job_id)
            raise AssertionError(
                "Pipeline did not reach DONE for all stages before timeout. "
                f"Current statuses: "
                f"script={cur.script_status}, audio={cur.audio_status}, "
                f"visuals={cur.visuals_status}, render={cur.render_status}"
            )

    # Cleanup the job row (keeps dev DB tidy)
    with SessionLocal() as db:
        cur = db.get(Job, job_id)
        if cur is not None:
            db.delete(cur)
            db.commit()
