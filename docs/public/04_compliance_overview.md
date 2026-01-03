# Compliance Overview (Public Summary)

This document summarizes the compliance posture of Sleepy Factory at a public-safe level.

It is written as an engineering approach to platform risk:
- make compliance measurable
- keep audit artifacts
- gate releases on deterministic checks

## Guiding principles

1) **Compliance is engineered, not improvised**
- Policy risk is treated like an operational threat model.
- Critical steps are modeled as state transitions and checklists.

2) **Auditability is non-negotiable**
- For each published asset, the system should be able to reconstruct:
  - what inputs were used
  - what transformations occurred
  - what outputs were produced
  - what disclosures were applied

3) **Safe-by-default publishing**
- Prefer staged rollout patterns (for example: unlisted first) when appropriate.
- Keep a probation window for automated copyright systems when content sources may trigger false positives.

## Required audit artifacts (conceptual)

Planned artifacts include:
- Artifact manifest(s) with hashes for key deliverables
- Transformation summary (high-level explanation of how content was produced)
- Prompt/version/model identifiers (without exposing prompt text publicly)
- Upload metadata snapshot and disclosure decision record

## Synthetic / altered content disclosure

The system treats disclosure as a structured decision:
- a decision is recorded as data
- the upload metadata includes disclosure fields when required
- verification checks confirm the intended disclosure state matches what the API reports

Exact policy mapping and decision trees are maintained privately, but the public concept is:
- disclosure is a required gate, not a manual afterthought

## API operations (high level)

Planned upload behavior emphasizes reliability:
- resumable uploads
- retry with backoff
- idempotent record keeping (attempt logs, session persistence)
- quota preflight checks before initiating expensive upload flows

## Data retention (high level)

Retention is treated as a compliance and debugging tool:
- keep final masters and manifests long enough to support appeals and investigations
- keep intermediate artifacts long enough to reproduce issues
- make retention configurable by channel/format

## What’s private
Detailed runbooks and edge-case handling (enforcement responses, appeals, platform-specific escalation flows) are maintained privately within ObsidianTroveLLC.
