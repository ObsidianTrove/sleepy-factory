# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on Keep a Changelog, but kept intentionally lightweight for a fast-moving codebase.

## Unreleased

### Documentation
- Add public, portfolio-safe design notes under `docs/public/`
- Update README to reference the design docs set

## 0.1.0 (2026-01-02)

### Added
- Postgres-backed job state machine with stage statuses (`audio`, `visuals`, `render`)
- Concurrency-safe job claiming using `SELECT ... FOR UPDATE SKIP LOCKED`
- Per-stage leases (`<stage>_lease_owner`, `<stage>_lease_expires_at`) for crash-safe processing
- Recovery loop to re-queue jobs with expired leases
- Orchestrator loop to advance jobs between stages
- `sf dev` command to run orchestrator, recovery, and workers in a single terminal (via `uv run sf dev`)

### Infrastructure
- Docker Compose Postgres for local development (`docker-compose.yml`)
- `uv` environment management with `uv.lock` for reproducible installs
- `ruff` linting and formatting configuration
- Alembic migrations with `DATABASE_URL` sourced from `.env` / environment variables
- GitHub Actions CI for Ruff checks and pytest tests

### Notes
- Current stage workers simulate work. Real generation and rendering stages will be added incrementally.
