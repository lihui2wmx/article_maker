# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-03

**Active next phase:** Phase 6A — typed research-planning task contracts  
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
| Phase 5C — reviewed Experiment-output-to-Evidence bridge | COMPLETE | PR #15 |

## Phase 5C closure

**Branch:** `phase/5c-experiment-evidence-bridge`  
**Integration carrier:** PR #15  
**Initial PR CI:** `33702257494` — success  
**Latest-head PR CI:** `33702321170` — success  
**Integrated main commit:** `f7c95d8bb9609a8192be7a2a30278985792aa723`  
**Merged-main CI:** `33702381621` — success

Phase 5C added deterministic reviewed promotion of explicit ExperimentRun provenance into canonical Evidence with:

- explicit Experiment + Run + Artifact + optional locator selections;
- exact output/diagnostic provenance membership and ambiguity rejection;
- current Run-to-Experiment spec-digest validation;
- selected Artifact manifest and filesystem/checksum audit;
- deterministic `ev-exp-*` Evidence identities and mechanical descriptions;
- output -> `EvidenceKind.EXPERIMENT_RESULT` and diagnostic -> `EvidenceKind.OTHER`;
- Experiment ID, Run ID, spec digest, operational run status, Artifact ID/role/locator, Run digest, and Artifact-manifest digest traceability;
- read-only plan generation and exact reviewed plan digest binding;
- execution-time Experiment/Run/Artifact stale-state validation;
- deterministic preview regeneration to reject arbitrary Evidence tampering;
- explicit canonical Evidence writes only during reviewed execution;
- existing-Evidence conflict rejection;
- post-write exact reload and structural Claim/Evidence audit;
- best-effort in-process rollback for newly written Evidence files.

Scientific interpretation remains separate. Phase 5C does not judge correctness, significance, reproduction success, support/contradiction, approve Claims/Hypotheses, execute experiments, invoke LLM/agent runtimes, or generate manuscript text.

Documentation:

- `docs/EXPERIMENT_EVIDENCE_BRIDGE.md`
- `docs/decisions/ADR-0014-reviewed-experiment-evidence-promotion.md`

## Next bounded increment — Phase 6A: typed research-planning task contracts

**Status:** READY after Phase 5C integration.

### Objective

Define framework-neutral contracts for bounded research-planning tasks and recommendations that agents may propose without giving agents authority to approve canonical scientific state or execute unbounded work.

### Initial boundary

Phase 6A should define at minimum:

- stable planning-task identity;
- task kind and bounded objective;
- references to ResearchQuestion/Hypothesis/Claim/Artifact/Citation/Experiment where applicable;
- proposer attribution;
- priority/rationale as proposal metadata rather than scientific truth;
- explicit task lifecycle/status separated from scientific approval;
- dependencies and completion-evidence references;
- human decision/authorization boundary for high-impact transitions;
- framework-neutral JSON Schema and Python validation.

### Non-goals

Do not introduce in Phase 6A:

- autonomous agent loops;
- provider-specific agent frameworks;
- automatic execution of proposed experiments;
- automatic scientific approval;
- manuscript generation;
- submission automation.
