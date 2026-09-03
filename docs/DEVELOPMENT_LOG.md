# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-03

**Active next phase:** Phase 6B — repository planning-task registry and authorization/dependency audit  
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
| Phase 6A — typed research-planning task contracts | COMPLETE | PR #16 |

## Phase 6A closure

**Branch:** `phase/6a-planning-task-contracts`  
**Integration carrier:** PR #16  
**Initial PR CI:** `33703967034` — success  
**Latest-head PR CI:** `33704050234` — success  
**Integrated main commit:** `4a47882e5a6818b00a876849a7437b3a7f63a022`  
**Merged-main CI:** `33704133107` — success

Phase 6A added framework-neutral bounded research-planning contracts with:

- stable `ptask-*` PlanningTask identity and shared validation;
- explicit PlanningTask kind, operational status, proposer, priority/rationale, dependencies, completion references, and JSON metadata;
- `PlanningTaskScope` with one bounded objective, at least one completion criterion, optional constraints, and optional non-goals;
- typed references to ResearchQuestion, Hypothesis, Claim, Evidence, Artifact, Citation, LiteratureNote, Experiment, and ExperimentRun state;
- duplicate/direct-self dependency rejection at the domain-contract layer;
- operational task lifecycle explicitly separated from scientific approval;
- durable typed completion references required only for completed tasks;
- canonical human `Decision` reuse via `DecisionSubjectType.PLANNING_TASK`;
- human Decision binding before human-gated tasks enter execution-eligible states;
- hard human gating for `experiment_execution`, including a concrete Experiment reference and ExperimentRun completion provenance;
- standard Draft 2020-12 planning-task schema, with cross-instance self-dependency comparison deliberately retained as a Python/domain invariant rather than a non-standard Schema extension;
- Python/JSON Schema positive and negative tests plus Phase 2 registry compatibility coverage.

PlanningTask completion remains an operational fact only. It does not resolve a ResearchQuestion, accept a Hypothesis, approve a Claim, interpret Evidence, establish scientific validity or reproduction success, approve manuscript text, or grant an executor unrestricted capability.

Documentation:

- `docs/PLANNING_TASK_CONTRACTS.md`
- `docs/decisions/ADR-0015-bounded-planning-tasks-and-human-authorization.md`

### Phase 6A exit conditions

- [x] stable PlanningTask identity and typed contract exist;
- [x] bounded scope and completion criteria are explicit;
- [x] canonical typed references exist;
- [x] dependencies and direct self-dependency checks exist;
- [x] operational lifecycle is separated from scientific state;
- [x] human Decision authorization boundary exists;
- [x] experiment execution is hard-gated to human authorization;
- [x] completed tasks require durable completion references;
- [x] Draft 2020-12 schema and Pydantic tests exist;
- [x] Phase 2 compatibility regression exists;
- [x] ADR-0015 records material decisions;
- [x] bounded-scope audit passes;
- [x] initial PR CI passes (`33703967034`);
- [x] latest-head PR CI passes (`33704050234`);
- [x] PR #16 squash merged (`4a47882e5a6818b00a876849a7437b3a7f63a022`);
- [x] merged `main` CI passes (`33704133107`).

## Next bounded increment — Phase 6B: repository planning-task registry and authorization/dependency audit

**Status:** READY after Phase 6A integration.

### Objective

Persist PlanningTask records in deterministic repository locations and audit repository-level task references, human authorization Decisions, task dependencies, completion references, and lifecycle consistency without executing tasks.

### Initial boundary

Phase 6B should at minimum:

- define one canonical repository location for `ptask-*` records;
- provide deterministic save/load/list APIs;
- resolve every typed PlanningReference against the appropriate Phase 1–5 registry;
- resolve `depends_on_task_ids`, detect missing dependencies, direct/transitive cycles, and duplicate IDs/layout mismatches;
- resolve human-gated `governing_decision_id` against `research/decisions/`;
- verify Decision subject/backlink and approve/reject outcome against task authorization state without treating operational completion as scientific approval;
- resolve completed-task `completion_refs` and report missing completion state;
- tolerate malformed records and continue audit;
- remain read-only during audit and avoid scheduling/executing work.

### Non-goals

Do not introduce in Phase 6B:

- autonomous agent loops;
- task scheduling or workers;
- provider-specific agent frameworks;
- experiment execution;
- automatic scientific approval;
- manuscript generation;
- submission automation.
