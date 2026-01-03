import os
import shutil
import socket
import subprocess
import threading
from datetime import UTC, datetime

from rich import print
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from sleepy_factory.artifacts import (
    ArtifactRecord,
    append_manifest,
    job_dir,
    stage_dir,
    write_json,
    write_text,
    write_bytes,
)
from sleepy_factory.db.models import Job, StageStatus
from sleepy_factory.db.session import SessionLocal

STAGES = ["script", "audio", "visuals", "render"]


def stage_fields(stage: str) -> tuple[str, str, str]:
    return (
        f"{stage}_status",
        f"{stage}_lease_owner",
        f"{stage}_lease_expires_at",
    )


def orchestrator_tick(db: Session) -> int:
    moved = 0

    # script: NEW -> READY
    q = select(Job).where(Job.script_status == StageStatus.NEW).limit(50)
    jobs = list(db.execute(q).scalars())
    for job in jobs:
        job.script_status = StageStatus.READY
        moved += 1

    # audio: gate on script DONE
    q = (
        select(Job)
        .where(
            Job.script_status == StageStatus.DONE,
            Job.audio_status == StageStatus.NEW,
        )
        .limit(50)
    )
    jobs = list(db.execute(q).scalars())
    for job in jobs:
        job.audio_status = StageStatus.READY
        moved += 1

    # visuals: gate on audio DONE
    q = (
        select(Job)
        .where(
            Job.audio_status == StageStatus.DONE,
            Job.visuals_status == StageStatus.NEW,
        )
        .limit(50)
    )
    jobs = list(db.execute(q).scalars())
    for job in jobs:
        job.visuals_status = StageStatus.READY
        moved += 1

    # render: gate on visuals DONE
    q = (
        select(Job)
        .where(
            Job.visuals_status == StageStatus.DONE,
            Job.render_status == StageStatus.NEW,
        )
        .limit(50)
    )
    jobs = list(db.execute(q).scalars())
    for job in jobs:
        job.render_status = StageStatus.READY
        moved += 1

    db.commit()
    return moved


def claim_one_job_for_stage(db: Session, stage: str, lease_minutes: int = 10) -> Job | None:
    now = datetime.now(UTC)
    owner = f"{socket.gethostname()}:{os.getpid()}:{stage}"

    status_field, lease_owner_field, lease_expires_field = stage_fields(stage)
    status_col = getattr(Job, status_field)

    q = (
        select(Job)
        .where(status_col == StageStatus.READY)
        .with_for_update(skip_locked=True)
        .limit(1)
    )

    job = db.execute(q).scalars().first()
    if not job:
        return None

    setattr(job, status_field, StageStatus.RUNNING)
    setattr(job, lease_owner_field, owner)
    setattr(job, lease_expires_field, Job.new_lease_expiry(now, minutes=lease_minutes))

    job.attempts += 1
    job.last_error = None

    db.commit()
    db.refresh(job)
    return job


def run_stage_work(job_id: str, stage: str) -> None:
    if stage == "script":
        script_md = (
            "# Video Script\n\n"
            "## Hook\n"
            "Write a short hook here.\n\n"
            "## Main Points\n"
            "1. Point one\n"
            "2. Point two\n"
            "3. Point three\n\n"
            "## Outro\n"
            "Closing wrap-up.\n"
        )
        script_obj = {
            "version": "0.1",
            "sections": [
                {"name": "hook", "text": "Write a short hook here."},
                {"name": "main_points", "bullets": ["Point one", "Point two", "Point three"]},
                {"name": "outro", "text": "Closing wrap-up."},
            ],
        }
        write_text(job_id, "script", "script.md", script_md, kind="script_markdown")
        write_json(job_id, "script", "script.json", script_obj, kind="script_structured")
        return

    if stage == "render":
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            write_text(
                job_id,
                "render",
                "final.txt",
                "ffmpeg not found. Install ffmpeg to generate final.mp4.\n",
                kind="final_output_notice",
            )
            write_json(
                job_id,
                "render",
                "render_plan.json",
                {
                    "status": "needs_ffmpeg",
                    "output": "final.mp4",
                    "placeholder": "final.txt",
                },
                kind="render_plan",
            )
            return


        out_dir = stage_dir(job_id, "render")
        out_path = out_dir / "final.mp4"

        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=1280x720:d=6",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=stereo",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(out_path),
        ]
        subprocess.run(cmd, check=True)

        data = out_path.read_bytes()
        write_bytes(job_id, "render", "final.mp4", data, kind="final_video")
        return

    # audio + visuals: still simulated for now
    return


def complete_job_stage(
    db: Session,
    job_id,
    owner: str,
    stage: str,
    success: bool,
    error: str | None = None,
) -> bool:
    status_field, lease_owner_field, lease_expires_field = stage_fields(stage)

    q = select(Job).where(Job.id == job_id).with_for_update()
    job = db.execute(q).scalars().first()
    if not job:
        return False

    if getattr(job, status_field) != StageStatus.RUNNING:
        return False

    if getattr(job, lease_owner_field) != owner:
        return False

    setattr(job, status_field, StageStatus.DONE if success else StageStatus.ERROR)
    job.last_error = None if success else (error or "unknown error")

    setattr(job, lease_owner_field, None)
    setattr(job, lease_expires_field, None)

    db.commit()
    return True


def run_worker_loop(
    stage: str, poll_seconds: float = 1.0, stop_event: threading.Event | None = None
):
    if stop_event is None:
        stop_event = threading.Event()

    owner = f"{socket.gethostname()}:{os.getpid()}:{stage}"
    print(f"[bold]Worker starting[/bold] ({stage}) as {owner}")

    while not stop_event.is_set():
        with SessionLocal() as db:
            job = claim_one_job_for_stage(db, stage=stage)
            if not job:
                stop_event.wait(poll_seconds)
                continue

        print(f"[{stage}] Claimed job {job.id} (attempt {job.attempts})")

        # Do work outside the DB transaction
        try:
            run_stage_work(str(job.id), stage)
            success = True
            err: str | None = None
        except Exception as exc:  # noqa: BLE001
            success = False
            err = f"{type(exc).__name__}: {exc}"

        with SessionLocal() as db:
            ok = complete_job_stage(
                db, job.id, owner=owner, stage=stage, success=success, error=err
            )
            print(f"[{stage}] Completed job {job.id}: {ok} (success={success})")


def run_orchestrator_loop(poll_seconds: float = 1.0, stop_event: threading.Event | None = None):
    if stop_event is None:
        stop_event = threading.Event()

    print("[bold]Orchestrator loop starting[/bold]")
    while not stop_event.is_set():
        with SessionLocal() as db:
            moved = orchestrator_tick(db)
        if moved:
            print(f"[orchestrator] moved {moved} stage transitions to READY")
        stop_event.wait(poll_seconds)


def recover_expired_leases(db: Session, limit: int = 50) -> int:
    now = datetime.now(UTC)

    conditions = []
    for stage in STAGES:
        status_field, _, lease_expires_field = stage_fields(stage)
        conditions.append(
            and_(
                getattr(Job, status_field) == StageStatus.RUNNING,
                getattr(Job, lease_expires_field).is_not(None),
                getattr(Job, lease_expires_field) < now,
            )
        )

    q = select(Job).where(or_(*conditions)).with_for_update(skip_locked=True).limit(limit)

    jobs = list(db.execute(q).scalars())
    recovered = 0

    for job in jobs:
        for stage in STAGES:
            status_field, lease_owner_field, lease_expires_field = stage_fields(stage)

            if getattr(job, status_field) == StageStatus.RUNNING:
                exp = getattr(job, lease_expires_field)
                if exp is not None and exp < now:
                    setattr(job, status_field, StageStatus.READY)
                    job.last_error = f"lease expired, re-queued {stage}"
                    setattr(job, lease_owner_field, None)
                    setattr(job, lease_expires_field, None)
                    recovered += 1
                    break

    db.commit()
    return recovered


def run_recovery_loop(poll_seconds: float = 5.0, stop_event: threading.Event | None = None):
    if stop_event is None:
        stop_event = threading.Event()

    print("[bold]Recovery loop starting[/bold]")
    while not stop_event.is_set():
        with SessionLocal() as db:
            n = recover_expired_leases(db)
        if n:
            print(f"[recovery] recovered {n} jobs with expired leases")
        stop_event.wait(poll_seconds)


def create_new_job():
    with SessionLocal() as db:
        job = Job()
        db.add(job)
        db.commit()
        db.refresh(job)
        print(
            "Created job "
            f"{job.id} (script={job.script_status}, audio={job.audio_status}, visuals={job.visuals_status}, "
            f"render={job.render_status})"
        )


def list_jobs(limit: int = 20):
    with SessionLocal() as db:
        q = select(Job).order_by(Job.created_at.desc()).limit(limit)
        jobs = list(db.execute(q).scalars())

    for j in jobs:
        print(
            f"{j.id}  "
            f"script={j.script_status}({j.script_lease_owner})  "
            f"audio={j.audio_status}({j.audio_lease_owner})  "
            f"visuals={j.visuals_status}({j.visuals_lease_owner})  "
            f"render={j.render_status}({j.render_lease_owner})  "
            f"attempts={j.attempts}"
        )


def run_dev(orchestrator_poll: float = 1.0, recovery_poll: float = 5.0):
    stop_event = threading.Event()

    threads: list[threading.Thread] = [
        threading.Thread(
            target=run_orchestrator_loop,
            kwargs={"poll_seconds": orchestrator_poll, "stop_event": stop_event},
            daemon=True,
        ),
        threading.Thread(
            target=run_recovery_loop,
            kwargs={"poll_seconds": recovery_poll, "stop_event": stop_event},
            daemon=True,
        ),
        threading.Thread(
            target=run_worker_loop,
            kwargs={"stage": "script", "stop_event": stop_event},
            daemon=True,
        ),
        threading.Thread(
            target=run_worker_loop, kwargs={"stage": "audio", "stop_event": stop_event}, daemon=True
        ),
        threading.Thread(
            target=run_worker_loop,
            kwargs={"stage": "visuals", "stop_event": stop_event},
            daemon=True,
        ),
        threading.Thread(
            target=run_worker_loop,
            kwargs={"stage": "render", "stop_event": stop_event},
            daemon=True,
        ),
    ]

    print("[bold]Sleepy Factory dev mode starting[/bold] (Ctrl+C to stop)")
    for t in threads:
        t.start()

    try:
        while True:
            stop_event.wait(0.5)
    except KeyboardInterrupt:
        print("\n[bold]Stopping...[/bold]")
        stop_event.set()
        for t in threads:
            t.join(timeout=2.0)
        print("[bold]Stopped.[/bold]")


def main():
    import argparse

    parser = argparse.ArgumentParser(prog="sf")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("new-job")

    p_list = sub.add_parser("list-jobs")
    p_list.add_argument("--limit", type=int, default=20)

    sub.add_parser("orchestrator")

    p_oloop = sub.add_parser("orchestrator-loop")
    p_oloop.add_argument("--poll", type=float, default=1.0)

    p_worker = sub.add_parser("worker")
    p_worker.add_argument("--stage", choices=STAGES, default="script")

    p_rec = sub.add_parser("recovery")
    p_rec.add_argument("--poll", type=float, default=5.0)

    p_dev = sub.add_parser("dev")
    p_dev.add_argument("--orchestrator-poll", type=float, default=1.0)
    p_dev.add_argument("--recovery-poll", type=float, default=5.0)

    args = parser.parse_args()

    if args.cmd == "dev":
        run_dev(orchestrator_poll=args.orchestrator_poll, recovery_poll=args.recovery_poll)
        return

    if args.cmd == "orchestrator-loop":
        run_orchestrator_loop(poll_seconds=args.poll)
        return

    if args.cmd == "recovery":
        run_recovery_loop(poll_seconds=args.poll)
        return

    if args.cmd == "new-job":
        create_new_job()
        return

    if args.cmd == "list-jobs":
        list_jobs(limit=args.limit)
        return

    if args.cmd == "orchestrator":
        with SessionLocal() as db:
            n = orchestrator_tick(db)
            print(f"Orchestrator moved {n} stage transitions to READY")
        return

    if args.cmd == "worker":
        run_worker_loop(stage=args.stage)
        return
