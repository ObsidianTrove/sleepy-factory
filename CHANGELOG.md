# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on Keep a Changelog, but kept intentionally lightweight for a fast-moving codebase.

## Version 0.1.2 - 2026-01-03

### Added
- Deterministic placeholder stage outputs for local development:
  - `audio/audio.wav` (short silent WAV) + `audio/audio_plan.json`
  - `visuals/cover.svg` (simple SVG cover) + `visuals/visuals_plan.json`
  - `render/render_plan.json` (documents whether `final.mp4` was produced or a fallback was written)
- `sf clean-artifacts` command to delete the local `./artifacts/` directory
- Smoke tests:
  - Manifest test that runs stage work and asserts expected `manifest.json` entries
  - End-to-end DB-backed smoke test that drives a job through all stages to `DONE`
- CI workflow split:
  - Fast CI runs lint/format + `pytest -m "not smoke"`
  - Separate `Smoke (DB)` workflow (manual + scheduled) that runs migrations and `pytest -m smoke` against a Postgres service container

### Changed
- GitHub Actions CI no longer requires Postgres on every push/PR (smoke is run separately)
- Pytest marker configuration updated to register the `smoke` mark

## Version 0.1.1 - 2026-01-03

### Added
- New `script` pipeline stage with status and per-stage lease fields
- Artifact system (`sleepy_factory/artifacts.py`) with per-job `manifest.json`
- Script stage outputs (`script.md`, `script.json`) written under `./artifacts/<job_id>/`
- Render stage can generate a real `final.mp4` when `ffmpeg` is available (fallback artifact when not)

### Changed
- Pipeline stage order is now `script -> audio -> visuals -> render`
- `.gitignore` now excludes generated `artifacts/` output

## Version 0.1.0 - 2026-01-02

### Added
- Postgres-backed job state machine with stage statuses (`audio`, `visuals`, `render`)
- Concurrency-safe job claiming using `SELECT ... FOR UPDATE SKIP LOCKED`
- Per-stage leases (`<stage>_lease_owner`, `<stage>_lease_expires_at`) for crash-safe processing
- Recovery loop to re-queue jobs with expired leases
- Orchestrator loop to advance jobs between stages
- `uv run sf dev` command to run orchestrator, recovery, and workers in a single terminal

### Infrastructure
- Docker Compose Postgres for local development (`docker-compose.yml`)
- `uv` environment management with `uv.lock` for reproducible installs
- `ruff` linting and formatting configuration
- Alembic migrations with `DATABASE_URL` sourced from `.env` / environment variables
- GitHub Actions CI for Ruff checks and pytest tests

### Notes
- Current stage workers simulate work. Real generation and rendering stages will be added incrementally.
