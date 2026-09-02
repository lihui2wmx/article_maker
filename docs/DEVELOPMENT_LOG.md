# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-03

**Active phase:** Phase 5A — typed Experiment provenance contracts  
**Status:** IMPLEMENTED — PR #13 initial CI passed; latest-head/integration gates pending  
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
| Phase 5A — typed Experiment provenance contracts | INTEGRATION PENDING | PR #13 |

## Phase 5A — typed Experiment provenance contracts

**Branch:** `phase/5a-experiment-provenance-contracts`  
**Integration carrier:** PR #13  
**Initial PR CI:** run `33657449413` — success

### Objective

Define framework-neutral canonical contracts for reproducible Experiment intent and individual ExperimentRun execution provenance without implementing experiment scheduling/execution or interpreting experimental results scientifically.

### Implemented

- added stable `exp-*` Experiment IDs and `exprun-*` ExperimentRun IDs;
- added `Experiment` as intended protocol/specification state with title, objective, proposer, input/config Artifact references, JSON parameters, expected code provenance, expected execution environment, and JSON metadata;
- added deterministic `experiment_spec_digest()` over canonical JSON serialization of the complete validated Experiment specification;
- added `ExperimentRun` as one observed execution with the referenced Experiment ID/spec digest, operational lifecycle, timezone-aware timestamps, executor attribution, actual input/config Artifacts, resolved parameters, observed code/environment, output Artifacts, optional termination details, optional lineage, and JSON metadata;
- added `CodeProvenance` with required Git revision and explicit dirty-working-tree semantics;
- required `working_tree_diff_artifact_id` when `dirty=true` and forbade a diff Artifact when `dirty=false`;
- added `ExecutionEnvironment` with runtime, optional OS/architecture/container identity, environment Artifacts, and JSON metadata;
- added `RunTermination` for failed/cancelled/partial executions, including reason/stage/diagnostic Artifacts;
- added `RunLineage` relations `rerun` and `reproduction`, explicitly representing execution intent rather than successful scientific reproduction;
- enforced lifecycle invariants for planned/running/completed/failed/cancelled/partial runs;
- required timezone-aware timestamps and forbade `finished_at < started_at`;
- deliberately omitted scientific quality, significance, hypothesis-support, Evidence, and Claim fields from ExperimentRun;
- added Draft 2020-12 `schemas/experiment.schema.json`;
- added Python/Pydantic implementation in `src/article_maker/experiment.py` and exported the public contract API;
- documented contract semantics in `docs/EXPERIMENT_CONTRACTS.md`;
- recorded durable identity/provenance/lifecycle choices in `docs/decisions/ADR-0012-experiment-run-provenance-and-lifecycle.md`;
- added positive/negative tests for Python and JSON Schema contracts, deterministic spec digests, dirty-code provenance, lifecycle timestamps, partial/failure termination, lineage self-reference, duplicate Artifact refs, JSON-only configuration, and invalid identities/revisions/digests.

### Scientific authority boundary

Phase 5A records experiment intent and execution facts only.

A run with `status=completed` does **not** mean that:

- the result is correct;
- the result is statistically significant;
- the run reproduced a prior result successfully;
- a Hypothesis is supported or contradicted;
- an Evidence or Claim record should be created;
- the result is manuscript-ready.

Those transitions remain separate, reviewable scientific workflows.

### Validation and scope audit

- `main..phase/5a-experiment-provenance-contracts` is ahead-only and limited to Experiment contracts, shared IDs, exports, schema, tests, documentation/ADR, and this handoff state;
- initial PR #13 CI run `33657449413` completed successfully, including all existing Phase 1–4C tests and the new Phase 5A suite;
- no Experiment registry, scheduler, remote/cloud/HPC runner, container orchestration, parameter-sweep executor, statistical interpretation, reproducibility scoring, automatic Evidence/Claim creation, LLM/agent runtime, or manuscript generation was introduced.

### Phase 5A exit conditions

- [x] Experiment and ExperimentRun identities exist;
- [x] intended Experiment and observed ExperimentRun are separate contracts;
- [x] exact Experiment specification digest exists;
- [x] input/config/code/environment/output provenance is explicit;
- [x] dirty code requires preserved diff provenance;
- [x] parameters/configuration are JSON-only canonical state;
- [x] operational lifecycle and failure/partial representation exist;
- [x] rerun/reproduction lineage is explicit and non-scientific;
- [x] Draft 2020-12 and Python contracts exist;
- [x] positive/negative tests exist;
- [x] ADR-0012 records material decisions;
- [x] bounded-scope audit passes;
- [x] initial PR CI passes;
- [ ] latest-head PR CI passes after this handoff update;
- [ ] PR #13 merged and `main` push CI passes.

## Next bounded increment — Phase 5B: repository Experiment registry and provenance audit

**Status:** BLOCKED until Phase 5A integration is complete.

### Objective

Persist Experiment and ExperimentRun records in deterministic repository locations and audit cross-record reproducibility/provenance integrity without executing jobs or interpreting results scientifically.

### Expected canonical layout

```text
experiments/<experiment-id>/experiment.json
experiments/<experiment-id>/runs/<run-id>.json
```

### Required audit boundary

At minimum Phase 5B should check:

- Experiment input/config/code/environment Artifact existence;
- ExperimentRun -> Experiment existence;
- ExperimentRun `experiment_spec_digest` matches the referenced canonical Experiment;
- run input/config/code/environment/output/diagnostic Artifact existence;
- dirty-code diff Artifact existence;
- filename/directory ID consistency and duplicate IDs;
- rerun/reproduction parent-run existence;
- run-lineage self/cycle detection across repository records;
- malformed-record tolerance;
- lifecycle/provenance findings remain structural/operational and do not infer scientific quality.

### Non-goals

Do not introduce in Phase 5B:

- job scheduling or execution;
- remote/cloud/HPC runners;
- parameter-sweep orchestration;
- automatic statistical/scientific interpretation;
- automatic Experiment-output-to-Evidence promotion;
- automatic ClaimEvidenceLink creation;
- reproducibility success scoring;
- LLM/agent orchestration;
- manuscript generation.
