# Stage Contracts (Public Summary)

This document describes stage boundaries and artifact expectations at a high level.

The internal specs define detailed schemas and QA gates. This public summary focuses on:
- what each stage is responsible for
- what it produces
- what “done” means

## Stage: Script (planned)

**Responsibility**
- Produce a per-segment script (or full script for short formats)
- Enforce tone, pacing, and structure rules for the channel’s format
- Run automated QA checks and rewrite if needed

**Produces (planned)**
- Script artifact(s): structured JSON + text per segment
- Segment summaries for later continuity checks
- QA report (rubric scores, lint results)
- Metadata manifest (prompt/version/model identifiers, timestamps)

**Notes**
- Prompt packs and rubric details are maintained privately.

## Stage: Audio (in repo as a simulated worker; real audio planned)

**Responsibility**
- Generate narration (TTS)
- Mix narration with ambience where applicable
- Enforce consistent loudness targets
- Produce segment audio and a master audio track

**Produces (planned)**
- Segment narration audio
- Segment mixed audio
- Master audio track (archival and delivery versions)
- Audio QA report (basic checks for clipping, silence, loudness range)

## Stage: Visuals (in repo as a simulated worker; real visuals planned)

**Responsibility**
- Generate or select visuals appropriate for the channel format
- Canonicalize video clips to a known video spec (for sync stability)
- Produce segment reels or segment video-only outputs

**Produces (planned)**
- Canonicalized clips
- Segment reel / segment video-only file
- Visual QA report (black frames, duration mismatches, encoding checks)

## Stage: Render (in repo as a simulated worker; real render planned)

**Responsibility**
- Assemble segments into a final master video
- Ensure A/V sync stability over long runtimes
- Apply final container, encoding, and mux rules
- Produce a final “upload-ready” master

**Produces (planned)**
- Final master video file (upload-ready)
- Master manifest: segment order, durations, checksums
- Render QA report

## Stage: Upload (planned)

**Responsibility**
- Perform resumable uploads
- Inject metadata atomically (title, description, tags, disclosures)
- Record upload IDs and final URLs
- Support “probation” workflows where content is first unlisted

**Produces (planned)**
- Upload record in DB with attempt history
- Final video URL + IDs
- Disclosure records and audit artifacts

## Stage: Analytics (planned)

**Responsibility**
- Pull post-publish metrics
- Feed cost governance decisions and scheduling
- Detect policy risk signals (strikes, claims, demonetization events)

**Produces (planned)**
- Time-series analytics records
- Alert events and health summaries

---

## Contract versioning

A key design goal is that every stage execution can be audited later.

Each run should record, at minimum:
- stage implementation version
- prompt pack / model identifiers (where relevant)
- input artifact IDs and output artifact IDs
- timestamps and worker identity

This enables reliable debugging and reproducibility.
