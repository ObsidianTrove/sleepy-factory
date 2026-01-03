# Sleepy Factory

Sleepy Factory is a Python-first, Postgres-backed pipeline skeleton for building a reliable, distributed-friendly "content factory" workflow.

It is intentionally built around production-proven primitives:

- A database-backed state machine (Postgres is the source of truth)
- Concurrency-safe job claiming using `SELECT ... FOR UPDATE SKIP LOCKED`
- Per-stage leases to safely recover work after crashes, sleeps, or restarts
- A small CLI (`sf`) that runs locally today and can evolve into a distributed system later
- On-disk artifact tracking with a per-job `manifest.json`

This repository is a foundation. The current implementation is a working pipeline simulator with real locking, real persistence, real recovery logic, and real on-disk artifacts. The next layers add real AI generation and media output.

---

## What this project is for

The long-term goal is to automate end-to-end YouTube video generation (as much as possible) across multiple formats:

- Long multi-hour "sleepy" videos
- 15 to 20 minute long-form informational videos
- Short-form content

This repo currently focuses on the reliability core: a state machine + orchestrator + workers + leases + recovery + artifact tracking.
Audio and visuals are currently placeholder outputs, designed to be deterministic and dependency-light.

---

## Pipeline model

Stages (in order):

1. `script`
2. `audio`
3. `visuals`
4. `render`

Each stage has:

- a status: `NEW`, `READY`, `RUNNING`, `DONE`, `ERROR`
- a lease owner: `<stage>_lease_owner`
- a lease expiry: `<stage>_lease_expires_at`

The orchestrator owns transitions between stages. Workers only claim and complete their own stage.

---

## Artifacts and outputs

Each job writes outputs to the local `./artifacts/` directory:

- `artifacts/<job_id>/manifest.json` is the single source of truth for produced files
- each stage writes into `artifacts/<job_id>/<stage>/...`

The `artifacts/` directory is intentionally git-ignored. It is generated output and can become very large (especially MP4s).

Current placeholder outputs:

- `script`
  - `script.md`
  - `script.json`
- `audio`
  - `audio.wav` (short silent WAV, no external dependencies)
  - `audio_plan.json`
- `visuals`
  - `cover.svg` (simple SVG cover, no external dependencies)
  - `visuals_plan.json`
- `render`
  - always writes `render_plan.json`
  - writes `final.mp4` if `ffmpeg` is available on PATH
  - otherwise writes `final.txt` describing what is missing

---

## Key features

- Deterministic state transitions stored in Postgres
- Concurrent worker claiming with `SKIP LOCKED` so multiple workers can run safely
- Per-stage lease fields so stuck jobs can be reclaimed safely
- Recovery loop that re-queues work whose lease has expired
- Dev mode: run orchestrator + recovery + all workers in a single terminal (`sf dev`)
- Tooling:
  - `uv` for environments + lockfile (`uv.lock`)
  - `ruff` for linting and formatting
  - `pytest` for tests (fast and DB-backed smoke tests)
  - GitHub Actions workflows (fast CI plus scheduled DB smoke)

---

## Requirements

- Windows + PowerShell (instructions are written for this setup)
- Python 3.14
- Docker Desktop (for local Postgres)
- `uv` installed
- `ffmpeg` (optional, only needed to generate `final.mp4`)

---

## Repository safety and licensing

This repository is proprietary.

No license is granted for use, copying, modification, or distribution.
It is published for evaluation and portfolio demonstration purposes.

See `LICENSE`.

---

## Step-by-step setup (Windows PowerShell)

### 1) Clone the repo

```powershell
git clone https://github.com/ObsidianTrove/sleepy-factory.git
cd sleepy-factory
```

### 2) Create your local `.env`

This repo does not commit `.env`. Create it from the template:

```powershell
Copy-Item .env.example .env
```

`.env.example` is configured for local Docker Compose Postgres:

```env
DATABASE_URL=postgresql+psycopg://dev:dev@localhost:5432/sleepy
```

### 3) Start Postgres (Docker Compose)

```powershell
docker compose up -d
docker compose ps
```

You should see a `postgres` container running.

### 4) Install dependencies with uv

```powershell
uv venv
uv sync --dev
```

### 5) Apply database migrations

```powershell
uv run alembic upgrade head
```

Optional checks:

```powershell
uv run alembic current
uv run alembic heads
```

---

## Running the pipeline

### Recommended: dev mode (one terminal)

This runs in a single process using threads:

- orchestrator loop
- recovery loop
- script worker
- audio worker
- visuals worker
- render worker

In a VS Code terminal:

```powershell
uv run sf dev
```

Stop it with `Ctrl+C`.

### Create jobs (in a second terminal)

```powershell
uv run sf new-job
uv run sf list-jobs
```

A completed job will show all stages as `DONE`.

---

## ffmpeg (optional)

If you want `render/final.mp4` to be generated, install ffmpeg and ensure it is on your PATH.

Verify:

```powershell
ffmpeg -version
```

If ffmpeg is not installed, the render stage still completes and will write `final.txt` plus `render_plan.json` to explain what is missing.

---

## CLI commands

Create a new job:

```powershell
uv run sf new-job
```

List recent jobs:

```powershell
uv run sf list-jobs --limit 20
```

Run the orchestrator once:

```powershell
uv run sf orchestrator
```

Run orchestrator loop:

```powershell
uv run sf orchestrator-loop --poll 1.0
```

Run recovery loop:

```powershell
uv run sf recovery --poll 5.0
```

Run a single stage worker:

```powershell
uv run sf worker --stage script
uv run sf worker --stage audio
uv run sf worker --stage visuals
uv run sf worker --stage render
```

Run everything in one process (dev mode):

```powershell
uv run sf dev
```

Delete all generated artifacts:

```powershell
uv run sf clean-artifacts
```

---

## How it works (technical overview)

### Orchestrator: transitions only

The orchestrator advances jobs through the pipeline:

- `script:  NEW -> READY`
- `audio:   NEW -> READY` only when `script=DONE`
- `visuals: NEW -> READY` only when `audio=DONE`
- `render:  NEW -> READY` only when `visuals=DONE`

Workers do not advance downstream stages. This keeps transitions deterministic and centralized.

### Workers: claim safely, then complete

Each worker:

1. Selects a `READY` job with `FOR UPDATE SKIP LOCKED`
2. Sets stage `READY -> RUNNING`
3. Writes lease fields (`<stage>_lease_owner`, `<stage>_lease_expires_at`)
4. Performs work outside the transaction
5. Completes only if the lease owner still matches

This prevents double-processing and supports horizontal scaling.

### Recovery: self-healing

If a process crashes or a machine sleeps during `RUNNING`, work can get stuck.

The recovery loop:

- finds `RUNNING` stages with expired leases
- re-queues them back to `READY`
- clears the lease fields

---

## Tests and CI

This repo has two types of tests:

- Fast tests (no database), run on every push and PR
- Smoke tests (require Postgres), run via a separate GitHub Actions workflow

### Run tests locally

Fast tests:

```powershell
uv run pytest -q
```

Smoke tests (requires Docker Postgres and migrations):

```powershell
docker compose up -d
uv run alembic upgrade head
uv run pytest -q -m smoke
```

### GitHub Actions workflows

- `CI` runs:
  - Ruff lint + format checks
  - `pytest -m "not smoke"`

- `Smoke (DB)` runs:
  - Postgres service container
  - migrations (`alembic upgrade head`)
  - `pytest -m smoke`

  It is triggered manually (`workflow_dispatch`) and also runs on a daily schedule.

---

## Project structure

```
sleepy_factory/
  cli.py                 # CLI entrypoint, orchestrator/workers, dev runner
  artifacts.py           # artifact helpers + per-job manifest.json
  config.py              # .env loading + required DATABASE_URL
  db/
    models.py            # SQLAlchemy models (jobs, enums, lease fields)
    session.py           # DB engine/session
    migrations/          # Alembic env + versions
.github/
  workflows/
    ci.yml               # Ruff + fast pytest (excludes smoke)
    smoke.yml            # Postgres + migrations + smoke tests (scheduled/manual)
docker-compose.yml       # local Postgres
pyproject.toml           # dependencies + tooling config
uv.lock                  # reproducible dependency lockfile
.env.example             # environment template
tests/                   # pytest tests (fast + smoke)
```

---

## Roadmap (high level)

This repo is deliberately building from the bottom up:

1. Reliability primitives (current)
2. Artifact storage + stage outputs (current, placeholder implementations)
3. Observability (structured logs, metrics)
4. Stage implementations:
   - prompt and script generation
   - audio synthesis
   - visual generation
   - video rendering
   - publishing and upload automation

---

## License

Copyright (c) 2026 ObsidianTroveLLC. All rights reserved.

This repository is proprietary. No license is granted for use, copying, modification, or distribution.
See `LICENSE`.
