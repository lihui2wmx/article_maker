# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-03

**Active phase:** Phase 5C — reviewed Experiment-output-to-Evidence proposal bridge  
**Status:** IMPLEMENTED — PR #15 initial CI passed; latest-head/integration gates pending  
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
| Phase 5C — reviewed Experiment-output-to-Evidence bridge | INTEGRATION PENDING | PR #15 |

## Phase 5C — reviewed Experiment-output-to-Evidence proposal bridge

**Branch:** `phase/5c-experiment-evidence-bridge`  
**Integration carrier:** PR #15  
**Initial PR CI:** `33702257494` — success

### Implemented

- added explicit `ExperimentEvidenceSelection` with Experiment ID, Run ID, Artifact ID, and optional locator;
- required each selected Artifact to belong to exactly one eligible Run provenance role: output or termination diagnostic;
- rejected ambiguous selections where the same Artifact is both output and diagnostic provenance;
- required the Run's `experiment_spec_digest` to match the current canonical Experiment before planning;
- loaded the selected Artifact manifest and required the Artifact to pass ArtifactRegistry audit, including checksum/path/status drift checks;
- added deterministic `ev-exp-*` Evidence identity generation;
- generated mechanical Evidence descriptions without accepting free-form scientific interpretation;
- mapped output provenance to `EvidenceKind.EXPERIMENT_RESULT` and diagnostic provenance to `EvidenceKind.OTHER`;
- preserved Experiment ID, Run ID, Experiment spec digest, operational Run status, Artifact ID, provenance role, locator, exact Run digest, and Artifact-manifest digest in bridge metadata;
- added read-only `ExperimentEvidencePlan` generation and deterministic `experiment_evidence_plan_digest()`;
- required exact reviewed digest binding before execution;
- reloaded and revalidated Experiment, Run, and Artifact provenance before any write;
- regenerated expected Evidence previews and required exact equality, preventing arbitrary Evidence injection even when a modified plan digest is recomputed;
- rejected existing Evidence identity conflicts;
- persisted canonical Evidence only during explicit `execute()`;
- performed post-write exact reload equality and structural Claim/Evidence audit;
- added best-effort in-process rollback for newly written Evidence files;
- added filesystem-backed tests for deterministic dry-run planning, failed-run diagnostics, ineligible/ambiguous provenance, stale Experiment specification, reviewed digest enforcement, Run drift, Artifact byte drift, preview tampering, successful persistence, and existing-Evidence conflicts;
- documented the bridge in `docs/EXPERIMENT_EVIDENCE_BRIDGE.md`;
- recorded durable decisions in `docs/decisions/ADR-0014-reviewed-experiment-evidence-promotion.md`.

### Scientific authority boundary

Phase 5C records explicitly selected execution provenance as Evidence material only.

It does **not**:

- interpret numerical results;
- judge correctness or statistical significance;
- determine reproduction success;
- create or accept ClaimEvidenceLink records;
- approve/reject Claims or Hypotheses;
- execute experiments or parameter sweeps;
- invoke an LLM or agent runtime;
- generate manuscript text.

`ExperimentRun.status=completed` and `Evidence.kind=experiment_result` remain provenance classifications, not scientific approval states.

### Validation and scope audit

- `main..phase/5c-experiment-evidence-bridge` is ahead-only and limited to bridge runtime, exports, tests, documentation/ADR, and this handoff state;
- initial PR #15 CI run `33702257494` completed successfully, including all existing Phase 1–5B tests and the new Phase 5C suite;
- no scheduler, experiment execution adapter, statistical analysis, reproducibility scoring, automatic Claim linking, LLM/agent orchestration, or manuscript generation was introduced.

### Phase 5C exit conditions

- [x] explicit Run + Artifact selection contract exists;
- [x] output/diagnostic provenance membership is enforced;
- [x] current Experiment spec digest is required;
- [x] Artifact manifest/filesystem provenance is checked;
- [x] deterministic dry-run Evidence previews exist;
- [x] exact review digest binding exists;
- [x] stale/tampered source state is rejected before persistence;
- [x] explicit execution is required for canonical Evidence write;
- [x] no automatic ClaimEvidenceLink or scientific interpretation is introduced;
- [x] filesystem-backed tests exist;
- [x] ADR-0014 records material decisions;
- [x] bounded-scope audit passes;
- [x] initial PR CI passes;
- [ ] latest-head PR CI passes after this handoff update;
- [ ] PR #15 merged and `main` push CI passes.

## Next bounded increment — Phase 6A: typed research-planning task contracts

**Status:** BLOCKED until Phase 5C integration is complete.

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
