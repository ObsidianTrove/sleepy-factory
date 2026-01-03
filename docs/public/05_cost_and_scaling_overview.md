# Cost and Scaling Overview (Public Summary)

This document describes the scaling philosophy of Sleepy Factory without exposing unit economics or vendor-specific cost tables.

## Why cost governance is part of the system

AI-driven media pipelines have a key failure mode:
- cost can scale faster than revenue if left unchecked

The system is designed to enforce:
- per-job spend caps
- stage-level gating before expensive steps
- “stop the line” triggers when quality or uniqueness controls fail

## Cost governance model (conceptual)

Planned cost governance includes:
- estimating cost before work starts (“quote”)
- tracking spend during execution (accumulated by stage/segment)
- enforcing a hard stop if projected cost exceeds configured limits
- tying spend increases to demonstrated performance (measured metrics, not hope)

## Scaling stages (conceptual)

A safe scaling plan typically looks like:

- **Stage 0: Single-channel MVP**
  - strict caps, high logging, optional human approval early
- **Stage 1: A few channels (highest risk)**
  - uniqueness controls, collision monitoring, conservative rollout
- **Stage 2: Small portfolio**
  - format diversification and infrastructure hardening
- **Stage 3: Larger portfolio**
  - clustering by resource profile, tighter automation gates

## Reliability constraints that impact scaling

Scaling is not just “more workers.” Real bottlenecks include:
- upload quotas and API limits
- render throughput per machine (thermal throttling, disk I/O, GPU/CPU constraints)
- object storage growth and retention costs

## Stop-the-line triggers (examples)

Examples of triggers that should pause expansion:
- repeated quality gate failures
- high cross-channel similarity signals
- elevated platform risk signals (claims, strikes, policy warnings)
- unstable costs or runaway retries

Exact thresholds are kept private, but the principle is:
- scale only when the system is stable and measurable

## What’s next
As real media stages are implemented, this document will be expanded with:
- measurable throughput metrics per stage
- monitoring dashboards and alerting
- cost attribution per artifact and per channel
