# Sleepy Factory

A Python-first, Postgres-backed pipeline skeleton for a reliable “content factory” style workflow.

This repo is intentionally boring and dependable: the core primitives are a state-machine stored in Postgres, workers that claim work with row locks (`FOR UPDATE SKIP LOCKED`), and per-stage leases so jobs are safe to retry and recover.

Current stages:
- `audio` → `visuals` → `render`

Key features:
- Deterministic state transitions stored in Postgres (single source of truth)
- Concurrent workers using `SKIP LOCKED` claiming
- Per-stage leases (`audio_lease_*`, `visuals_lease_*`, `render_lease_*`)
- Recovery loop that re-queues jobs with expired leases
- Orchestrator loop that advances jobs through stages
- `uv` for reproducible environments and a lockfile (`uv.lock`)
- `ruff` for linting and formatting

---

## Requirements

- Python 3.14
- Docker Desktop (for local Postgres)
- `uv` installed

---

## Configuration

This repo does not commit `.env`. Create a local `.env` from `.env.example`.

```powershell
Copy-Item .env.example .env
```

Example `.env`:

```env
DATABASE_URL=postgresql+psycopg://dev:dev@localhost:5432/sleepy
```

Notes:
- `DATABASE_URL` is required. If it is missing, commands will fail with a helpful error.
- If you have `DATABASE_URL` set in your shell or Windows environment variables, it can override local expectations. You can clear it for the current PowerShell session with:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
```

---

## Quickstart (Windows PowerShell)

### 1) Start Postgres
From the repo root:

```powershell
docker compose up -d
docker compose ps
```

### 2) Install dependencies with uv
For running the pipeline:

```powershell
uv venv
uv sync
```

For development (includes Ruff):

```powershell
uv sync --dev
```

### 3) Run database migrations
```powershell
uv run alembic upgrade head
```

### 4) Run the pipeline (recommended: 5 terminals)

Terminal 1 (orchestrator loop):
```powershell
uv run sf orchestrator-loop
```

Terminal 2 (recovery loop):
```powershell
uv run sf recovery
```

Terminal 3 (audio worker):
```powershell
uv run sf worker --stage audio
```

Terminal 4 (visuals worker):
```powershell
uv run sf worker --stage visuals
```

Terminal 5 (render worker):
```powershell
uv run sf worker --stage render
```

### 5) Create a job and watch it flow
In a new terminal:

```powershell
uv run sf new-job
uv run sf list-jobs
```

You should see the job progress stage-by-stage. Example output:

```
<job-id>  audio=RUNNING(<host:pid>)  visuals=NEW(None)  render=NEW(None)  attempts=1
```

As workers finish:
- `audio=DONE` triggers `visuals=READY`
- `visuals=DONE` triggers `render=READY`
- `render=DONE` completes the job

---

## Commands

Create a new job:
```powershell
uv run sf new-job
```

List recent jobs:
```powershell
uv run sf list-jobs --limit 20
```

Run a worker for a specific stage:
```powershell
uv run sf worker --stage audio
uv run sf worker --stage visuals
uv run sf worker --stage render
```

Run orchestrator (single tick vs loop):
```powershell
uv run sf orchestrator
uv run sf orchestrator-loop --poll 1.0
```

Run recovery loop:
```powershell
uv run sf recovery --poll 5.0
```

Alembic helpers:
```powershell
uv run alembic current
uv run alembic heads
uv run alembic revision --autogenerate -m "your message"
uv run alembic upgrade head
```

---

## Development

Lint and format (Ruff):
```powershell
uv run ruff check . --fix
uv run ruff format .
```

Check-only (CI style):
```powershell
uv run ruff check .
uv run ruff format --check .
```

Optional: Alembic post-write hooks  
If enabled in `alembic.ini`, new migration files can be automatically linted and formatted after generation.

---

## How the pipeline works

### Orchestrator (state transitions)
The orchestrator advances jobs by updating stage statuses in Postgres:

- `audio: NEW → READY`
- `visuals: NEW → READY` (only when `audio=DONE`)
- `render: NEW → READY` (only when `visuals=DONE`)

Workers do not advance downstream stages. They only complete their stage. The orchestrator owns transitions.

### Worker claiming (concurrency-safe)
Workers claim jobs with:
- `SELECT ... FOR UPDATE SKIP LOCKED`
- mark stage `READY → RUNNING`
- set a stage-specific lease (`<stage>_lease_owner`, `<stage>_lease_expires_at`)
- do work outside the transaction
- complete with a compare-and-set check (lease owner must match)

This pattern allows multiple workers to run concurrently with no duplicate processing.

### Recovery (self-healing)
If a worker crashes or the machine sleeps, a job can be stuck in `RUNNING`.
The recovery loop detects expired leases and re-queues that stage to `READY`.

---

## Project structure

```
sleepy_factory/
  cli.py                 # CLI entrypoint and worker/orchestrator loops
  config.py              # env/config loading (DATABASE_URL required)
  db/
    models.py            # SQLAlchemy models
    session.py           # DB engine/session
    migrations/          # Alembic migrations
docker-compose.yml       # local Postgres
pyproject.toml           # dependencies + tooling (uv + ruff)
uv.lock                  # reproducible dependency lockfile
.env.example             # environment template
```

---

## Notes

- This repo is a skeleton focused on reliability primitives first.
- Real implementations add artifact paths, stage outputs, observability, and an upload stage.

---

## License

Copyright (c) 2026 ObsidianTroveLLC. All rights reserved.

This repository is proprietary. No license is granted for use, copying, modification, or distribution.

