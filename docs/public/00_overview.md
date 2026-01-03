# Sleepy Factory (Public Design Notes)

These documents summarize the **public, portfolio-safe** design intent of the Sleepy Factory project.

They are written to be:
- **Honest** about what exists today versus what is planned.
- **Actionable** for a reviewer who wants to understand the system quickly.
- **Careful** about omitting proprietary prompt packs, vendor pricing details, and operational playbooks.

## What exists today (in this repo)

The current codebase implements the *reliability core*:

- A Postgres-backed job table storing **stage statuses** (`audio`, `visuals`, `render`)
- Workers that claim jobs using `SELECT ... FOR UPDATE SKIP LOCKED`
- Per-stage **leases** (owner + expiry) to safely recover abandoned work
- An orchestrator that advances jobs through the state machine
- A recovery loop that re-queues stages whose lease expired
- Local development via Docker Compose Postgres and a single-terminal `sf dev` runner

Today the stage workers simulate work. They prove the concurrency + recovery model end to end.

## What the system is intended to become

The long-term goal is a modular “content factory” capable of automating AI-assisted YouTube video creation across multiple formats:

- Multi-hour “sleep” videos
- 15–20 minute longform informational videos
- Shorts under 60 seconds

The design assumes a pipeline of specialized workers (script → audio → visuals → render → upload → analytics), coordinated by a database control plane.

## Why Postgres is the control plane

Postgres is used as the single source of truth for:

- Job lifecycle and stage state
- Idempotency guarantees (what is safe to retry)
- Lease ownership and recovery
- Artifact manifests (what was produced, where it lives, with hashes)
- Audit artifacts and compliance metadata (in later stages)

This creates a system that can be:
- scaled horizontally (more worker processes and machines)
- paused/resumed safely
- inspected and debugged with direct database queries

## What is intentionally not included here

To keep the public repo safe and non-cloneable, these docs **do not include**:

- Full prompt texts or prompt matrices
- Detailed “runbook” instructions for platform enforcement edge cases
- Vendor-specific pricing tables, profit thresholds, or channel strategy

Those can exist privately within ObsidianTroveLLC.

## Documents in this folder

- `01_architecture.md` — components, data boundaries, and reliability principles
- `02_state_machine_and_leases.md` — worker claiming, leases, and recovery invariants
- `03_stage_contracts.md` — stage interfaces and artifact contracts (high level)
- `04_compliance_overview.md` — compliance posture and audit artifacts (high level)
- `05_cost_and_scaling_overview.md` — scaling philosophy and cost governance (high level)
