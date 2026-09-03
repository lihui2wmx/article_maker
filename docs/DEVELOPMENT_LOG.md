# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-03

**Active phase:** Phase 5B — repository Experiment registry and provenance audit  
**Status:** IMPLEMENTED — PR #14 initial CI passed; latest-head/integration gates pending  
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
| Phase 5B — Experiment registry/provenance audit | INTEGRATION PENDING | PR #14 |

## Phase 5B — repository Experiment registry and provenance audit

**Branch:** `phase/5b-experiment-registry`  
**Integration carrier:** PR #14  
**Initial PR CI:** `33700963581` — success

### Implemented

- added `ExperimentRegistry` in `src/article_maker/experiment_registry.py`;
- canonical layout:
  - `experiments/<experiment-id>/experiment.json`;
  - `experiments/<experiment-id>/runs/<run-id>.json`;
- deterministic UTF-8 JSON persistence with same-directory atomic replace;
- typed save/load/list APIs for Experiment and ExperimentRun;
- malformed-record-tolerant read-only repository audit;
- Experiment Artifact audit for inputs, configs, code snapshots, dirty-code diff, and environment Artifacts;
- Run -> Experiment existence audit;
- exact Run `experiment_spec_digest` verification against the current canonical Experiment;
- Run Artifact audit for inputs, configs, code, dirty-code diff, environment, outputs, and termination diagnostics;
- Experiment directory identity and duplicate Experiment ID audit;
- Run filename/storage-directory identity and duplicate Run ID audit;
- rerun/reproduction parent existence audit;
- repository-level Run lineage cycle detection;
- exported registry API from package root;
- filesystem-backed tests for clean persistence, missing Experiment, spec drift, missing Artifacts, dirty-code diff provenance, missing lineage parents, lineage cycles, directory/filename mismatches, duplicate IDs, malformed records, unsafe paths, and typed missing loads;
- documented behavior in `docs/EXPERIMENT_REGISTRY.md`;
- recorded durable choices in `docs/decisions/ADR-0013-repository-experiment-registry-and-provenance-audit.md`.

### Scientific authority boundary

Phase 5B findings are structural and operational only. A clean registry does not establish scientific validity, statistical significance, successful reproduction, Hypothesis support, Evidence eligibility, Claim approval, or manuscript readiness.

The registry does not:

- execute or schedule jobs;
- launch remote/cloud/HPC workloads;
- expand parameter sweeps;
- compare numerical outcomes;
- score reproducibility success;
- promote Run outputs to Evidence;
- create ClaimEvidenceLink records;
- invoke an LLM or agent runtime.

### Validation and scope audit

- `main..phase/5b-experiment-registry` is ahead-only and limited to registry runtime, exports, tests, documentation/ADR, and this handoff state;
- initial PR #14 CI run `33700963581` completed successfully, including all existing Phase 1–5A tests and the new Phase 5B suite;
- no scheduler, execution adapter, parameter-sweep engine, reproducibility scoring, statistical interpretation, automatic Evidence/Claim creation, LLM/agent orchestration, or manuscript generation was introduced.

### Phase 5B exit conditions

- [x] deterministic Experiment/Run repository layout exists;
- [x] typed save/load/list APIs exist;
- [x] malformed-record-tolerant read-only audit exists;
- [x] Experiment and Run Artifact provenance is audited;
- [x] Run -> Experiment and exact spec digest are audited;
- [x] dirty-code diff provenance is audited;
- [x] directory/filename identity and duplicate IDs are audited;
- [x] lineage parent existence and cycles are audited;
- [x] filesystem-backed tests exist;
- [x] ADR-0013 records material decisions;
- [x] bounded-scope audit passes;
- [x] initial PR CI passes;
- [ ] latest-head PR CI passes after this handoff update;
- [ ] PR #14 merged and `main` push CI passes.

## Next bounded increment — Phase 5C: reviewed Experiment-output-to-Evidence proposal bridge

**Status:** BLOCKED until Phase 5B integration is complete.

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
