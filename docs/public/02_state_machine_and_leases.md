# State Machine and Leases

This document explains the reliability contract used throughout the pipeline.

## Stage statuses

Each stage uses the same status enum:

- `NEW` — stage exists but has not been made available
- `READY` — stage can be claimed by a worker
- `RUNNING` — a worker has claimed the stage and holds a lease
- `DONE` — stage completed successfully
- `ERROR` — stage failed (may be retried based on policy)

## Who is allowed to change what

### Orchestrator
- Advances stages from `NEW → READY` when prerequisites are met
- Never marks work `DONE`
- Does not “do” heavy work

### Workers
- Claim work: `READY → RUNNING` (and set a lease)
- Complete work: `RUNNING → DONE` (or `ERROR`)
- Never advance downstream stages

This separation keeps transitions deterministic and debuggable.

## Concurrency-safe claiming (SKIP LOCKED)

Workers claim work using:

- `SELECT ... FOR UPDATE SKIP LOCKED` to avoid multiple workers claiming the same row
- a transaction that:
  1) locks the row
  2) updates it to `RUNNING`
  3) writes lease metadata
  4) commits quickly

The expensive work happens outside the transaction.

## Per-stage leases

A lease contains:

- `<stage>_lease_owner` — a unique identifier for the claimant (host + pid + stage is sufficient for dev)
- `<stage>_lease_expires_at` — a timestamp after which the work is considered abandoned

### Completion is compare-and-set
Completion is accepted only if:
- stage is still `RUNNING`
- lease owner matches

This prevents a late/stale worker from overwriting progress after recovery.

## Recovery loop

The recovery loop periodically:
1. Finds stages that are `RUNNING` and whose lease is expired
2. Resets that stage to `READY`
3. Clears the lease fields
4. Records a diagnostic message for operators

This provides crash safety, sleep safety, and restart safety.

## Idempotency guidelines (practical)

As real stages are implemented, follow these rules:

- Write artifacts to deterministic paths (derived from job_id, segment_id, stage version)
- If an output already exists and passes validation, treat the stage as completed (or skip work)
- Keep “commit” actions last (for example: uploading, publishing, deleting)
- Record checksums/hashes for key outputs when feasible

## Planned: segment-level leases
For long videos, the same lease model applies at the segment level:
- a segment is a smaller work unit within a job
- recovery can re-queue only the failed segment
