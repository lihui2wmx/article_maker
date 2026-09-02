# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-03

**Active next phase:** Phase 5B — repository Experiment registry and provenance audit  
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

## Phase 5A closure

**Branch:** `phase/5a-experiment-provenance-contracts`  
**Integration carrier:** PR #13  
**Initial PR CI:** `33657449413` — success  
**Latest-head PR CI:** `33657556912` — success  
**Integrated main commit:** `e2b5db9aed662a03fa859d3531b1d98bbd1d0c0c`  
**Merged-main CI:** `33657647760` — success

Phase 5A added framework-neutral `Experiment` and `ExperimentRun` contracts with:

- stable `exp-*` and `exprun-*` identities;
- separation of intended Experiment specification from observed run provenance;
- deterministic `experiment_spec_digest()` binding runs to exact intended specifications;
- explicit input/config/code/environment/output Artifact references;
- Git revision and dirty-working-tree provenance, including required diff Artifact for dirty code;
- JSON-only intended/resolved parameter state;
- operational run states `planned`, `running`, `completed`, `failed`, `cancelled`, and `partial`;
- timezone-aware lifecycle timestamps and explicit termination provenance for incomplete terminal runs;
- `rerun` / `reproduction` lineage that records execution intent without asserting scientific reproduction success;
- Draft 2020-12 schema and Python/Pydantic validation;
- positive/negative contract tests and ADR-0012.

A completed run remains an execution fact only. Phase 5A does not infer correctness, statistical significance, reproducibility success, Hypothesis support, Evidence, Claim status, or manuscript readiness.

Documentation:

- `docs/EXPERIMENT_CONTRACTS.md`
- `docs/decisions/ADR-0012-experiment-run-provenance-and-lifecycle.md`

## Next bounded increment — Phase 5B: repository Experiment registry and provenance audit

**Status:** READY after Phase 5A integration.

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
