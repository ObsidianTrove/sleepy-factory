# Architecture

This document describes the system architecture at a level appropriate for a public repo.

## High-level components

### Postgres (Control Plane)
Postgres is the system of record for:
- Jobs and their lifecycle
- Stage statuses and transitions
- Lease ownership (who is allowed to complete a stage)
- Worker run logs (later)
- Artifact manifests (later)
- Upload/compliance metadata (later)

### Orchestrator (Scheduler)
A lightweight coordinator responsible for:
- creating or scheduling work (later: from channel calendars and topic backlogs)
- advancing jobs between stages when prerequisites are satisfied
- never performing heavy generation or rendering

### Workers (Consumers)
Independent processes that:
- claim a unit of work (job or segment) from the DB
- produce output artifacts
- write completion results back to the DB
- remain stateless beyond the DB contract

Planned worker types (not all implemented yet):
- Script Worker
- Audio Worker (TTS + mixing)
- Visual Worker (image/video generation, clip selection)
- Render Worker (segment assembly + final mux)
- Upload Worker (resumable uploads + metadata injection)
- Analytics Worker (post-publish metrics ingestion)

### Workspace + Storage
- Local disk (fast scratch) for intermediate outputs
- Object storage (S3-compatible) for immutable artifacts and long-term retention (planned)

## Operating principles

### 1) Database-first state machine
All lifecycle state lives in Postgres. If the DB says a stage is `RUNNING`, the system treats it as `RUNNING` even if a worker died.

### 2) Workers are retry-safe
Workers must be safe to retry. They should:
- write outputs to deterministic paths
- avoid non-idempotent side effects until the DB state says “commit”
- record enough metadata to prove what happened

### 3) Leases prevent split-brain completion
A worker that claims a job receives a lease. The system only accepts completion if:
- the stage is still `RUNNING`
- the lease owner matches
- the lease has not been cleared/reassigned

### 4) Recovery is a first-class feature
A dedicated recovery loop (or worker) scans for expired leases and re-queues stuck work safely.

## Data model (public summary)

The internal docs describe a richer schema for channels, segments, assets, uploads, and audits. Publicly, the important idea is:

- **Jobs** represent “produce one video”
- **Stages** represent deterministic steps in the pipeline
- **Artifacts** represent outputs produced by a stage (later: with hashes and manifests)
- **Segments** represent chunked work for long videos (planned)

This repo currently demonstrates the job + stage coordination model.

## Planned evolution: job-level → segment-level
Long-form videos are designed to be processed as segments so that:
- failures only reprocess the affected segment
- the system can parallelize within a single video
- multi-hour A/V sync stays stable via strict canonicalization rules
