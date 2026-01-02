# Sleepy Factory

Sleepy Factory is a Python-first, Postgres-backed pipeline skeleton for building a reliable “content factory” workflow.

It is intentionally built around boring, production-proven primitives:

- A **database-backed state machine** (Postgres is the source of truth)
- **Concurrency-safe job claiming** using `SELECT ... FOR UPDATE SKIP LOCKED`
- **Per-stage leases** to safely recover work after crashes, sleeps, or restarts
- A small CLI (`sf`) you can run locally today and evolve into a distributed system later

This repository is a foundation. The current implementation is a working pipeline simulator with real locking, real persistence, and real recovery logic. The next layers will add actual AI generation and media output.

---

## What this project is for

The long-term goal is to automate end-to-end YouTube video generation (as much as possible) across multiple formats:

- Long multi-hour “sleepy” videos
- 15–20 minute longform informational videos
- Shorts under 60 seconds

This repo currently focuses on the reliability core: a state machine + workers + leases + recovery. It does not yet implement real AI generation or rendering.

---

## Current pipeline model

Stages:

1. `audio`
2. `visuals`
3. `render`

Each stage has:

- a status: `NEW`, `READY`, `RUNNING`, `DONE`, `ERROR`
- a lease owner: `<stage>_lease_owner`
- a lease expiry: `<stage>_lease_expires_at`

The orchestrator owns the state transitions between stages. Workers only claim and complete their own stage.

---

## Key features

- **Deterministic state transitions stored in Postgres**
- **Concurrent worker claiming** with `SKIP LOCKED` so multiple workers can run safely
- **Per-stage lease fields** so stuck jobs can be reclaimed safely
- **Recovery loop** that re-queues work whose lease has expired
- **Dev mode**: run the full orchestrator + workers in a single terminal (`sf dev`)
- **Tooling**:
  - `uv` for environments + lockfile (`uv.lock`)
  - `ruff` for linting and formatting
  - GitHub Actions CI to keep the repo clean

---

## Requirements

- Windows + PowerShell (instructions are written for this setup)
- Python 3.14
- Docker Desktop
- `uv` installed

---

## Repository safety and licensing

This repository is proprietary.

**No license is granted for use, copying, modification, or distribution.**  
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

`.env.example` uses local Docker Compose Postgres:

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
Create a virtual environment and install dev dependencies:

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

### Recommended: Dev mode (one terminal)
This runs:
- orchestrator loop
- recovery loop
- audio worker
- visuals worker
- render worker

In one VS Code terminal:

```powershell
uv run sf dev
```

Stop it with `Ctrl+C`.

### Create jobs (in a second terminal)
```powershell
uv run sf new-job
uv run sf list-jobs
```

You’ll see jobs move through the stage machine. A completed job will show:

- `audio=DONE`
- `visuals=DONE`
- `render=DONE`
- `attempts=3` (one claim per stage)

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
uv run sf worker --stage audio
uv run sf worker --stage visuals
uv run sf worker --stage render
```

Run everything in one process (dev mode):
```powershell
uv run sf dev
```

---

## How it works (technical overview)

### Orchestrator: transitions only
The orchestrator advances jobs through the pipeline:

- `audio:   NEW → READY`
- `visuals: NEW → READY` only when `audio=DONE`
- `render:  NEW → READY` only when `visuals=DONE`

Workers do not advance downstream stages. This makes stage transitions deterministic and centralized.

### Workers: claim safely, then complete
Each worker:
1. Selects a `READY` job with `FOR UPDATE SKIP LOCKED`
2. Sets stage `READY → RUNNING`
3. Writes lease fields (`<stage>_lease_owner`, `<stage>_lease_expires_at`)
4. Performs work outside the transaction
5. Completes only if the lease owner still matches

This prevents double-processing and supports horizontal scaling.

### Recovery: self-healing
If a machine crashes or sleeps during `RUNNING`, the job can be stuck.

The recovery loop:
- finds `RUNNING` stages with expired leases
- re-queues them back to `READY`
- clears the lease fields

---

## Project structure

```
sleepy_factory/
  cli.py                 # CLI entrypoint, orchestrator/workers, dev runner
  config.py              # .env loading + required DATABASE_URL
  db/
    models.py            # SQLAlchemy models (jobs, enums, lease fields)
    session.py           # DB engine/session
    migrations/          # Alembic env + versions
.github/
  workflows/ci.yml        # Ruff + pytest checks via uv
docker-compose.yml        # local Postgres
pyproject.toml            # dependencies + tooling config
uv.lock                   # reproducible dependency lockfile
.env.example              # environment template
tests/                    # minimal test scaffolding (CI sanity)
```

---

## Development workflow

### Lint and format
```powershell
uv run ruff check . --fix
uv run ruff format .
```

### CI-style checks
```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

### Creating migrations
Autogenerate a migration after changing models:

```powershell
uv run alembic revision --autogenerate -m "describe change"
```

Apply migrations:

```powershell
uv run alembic upgrade head
```

---

## Roadmap (high level)

This repo is deliberately building from the bottom up:

1. Reliability primitives (current)
2. Artifact storage + stage outputs (paths, metadata, checksums)
3. Observability (structured logs, metrics)
4. Stage implementations:
   - script + prompt generation
   - audio synthesis
   - visual generation
   - video rendering
   - publishing / upload automation

---

## License

Copyright (c) 2026 ObsidianTroveLLC. All rights reserved.

This repository is proprietary. No license is granted for use, copying, modification, or distribution.
See `LICENSE`.
