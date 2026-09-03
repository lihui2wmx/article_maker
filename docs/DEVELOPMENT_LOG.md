# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-03

**Active next phase:** Phase 5C — reviewed Experiment-output-to-Evidence proposal bridge  
**Status:** READY  
**Default branch:** `main`

### Completed milestones

| Phase | Status | Integration carrier |
| --- | --- | --- |
| Phase 0 — repository foundation | COMPLETE | PR #1 |
| Phase 1A — typed Artifact manifest | COMPLETE | PR #2 |
| Phase 1B — deterministic Artifact registration/audit | COMPLETE | PR #3 |
| Phase 1C — bounded discovery + dry-run batch planning | COMPLETE | PR #4 |
| Phase 1D — reviewed batch-plan execution | COMPLETE | PR #5 |
| Phase 2A — ResearchQuestion/Hypothesis/Decision contracts | COMPLETE | PR #6 |
| Phase 2B — repository research-state registry/audit | COMPLETE | PR #7 |
| Phase 3A — Claim/Evidence governance contracts | COMPLETE | PR #8 |
| Phase 3B — repository Claim/Evidence registry/audit | COMPLETE | PR #9 |
| Phase 4A — Literature/Citation contracts | COMPLETE | PR #10 |
| Phase 4B — literature registry/citation-integrity audit | COMPLETE | PR #11 |
| Phase 4C — reviewed literature-to-Evidence bridge | COMPLETE | PR #12 |
| Phase 5A — typed Experiment provenance contracts | COMPLETE | PR #13 |
| Phase 5B — Experiment registry/provenance audit | COMPLETE | PR #14 |

## Phase 5B closure

**Branch:** `phase/5b-experiment-registry`  
**Integration carrier:** PR #14  
**Initial PR CI:** `33700963581` — success  
**Latest-head PR CI:** `33701039373` — success  
**Integrated main commit:** `b37ff7e2cc17b266f7d11c8fd19381f0b7f56c0c`  
**Merged-main CI:** `33701092603` — success

Phase 5B added repository-native Experiment persistence and read-only provenance audit with:

- canonical `experiments/<experiment-id>/experiment.json` and `runs/<run-id>.json` locations;
- deterministic UTF-8 JSON persistence and typed save/load/list APIs;
- malformed-record-tolerant global audit;
- Experiment and Run Artifact provenance resolution;
- exact Run-to-Experiment `experiment_spec_digest` verification;
- dirty-code diff and termination-diagnostic Artifact checks;
- directory/filename identity and duplicate-ID checks;
- rerun/reproduction parent existence and lineage-cycle detection.

All findings remain structural/operational. A clean registry does not imply scientific validity, statistical significance, reproduction success, Evidence eligibility, Claim support, or manuscript readiness.

Documentation:

- `docs/EXPERIMENT_REGISTRY.md`
- `docs/decisions/ADR-0013-repository-experiment-registry-and-provenance-audit.md`

## Next bounded increment — Phase 5C: reviewed Experiment-output-to-Evidence proposal bridge

**Status:** READY after Phase 5B integration.

### Objective

Create a deterministic, reviewable bridge from explicitly selected ExperimentRun output/diagnostic Artifacts to proposed `Evidence` records without inferring scientific meaning, support/contradiction, statistical significance, or reproduction success.

### Required boundary

At minimum Phase 5C should:

- accept only explicit Run + Artifact selections;
- require the selected Artifact to belong to the referenced Run's output or diagnostic provenance;
- preserve Experiment ID, Run ID, Experiment spec digest, execution status, Artifact ID, and optional locator in Evidence proposal metadata;
- generate deterministic dry-run Evidence previews;
- bind execution to an exact reviewed plan digest;
- reject stale Experiment/Run records or changed provenance before persistence;
- require explicit reviewed execution before canonical Evidence write;
- avoid creating ClaimEvidenceLink records or scientific interpretations automatically.

### Non-goals

Do not introduce in Phase 5C:

- experiment scheduling/execution;
- statistical significance or correctness judgments;
- automatic reproduction-success scoring;
- automatic ClaimEvidenceLink creation/acceptance;
- automatic Claim approval/rejection;
- LLM/agent orchestration;
- manuscript generation.
