# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-03

**Active phase:** Phase 6A — typed research-planning task contracts  
**Status:** IMPLEMENTED — PR #16 initial CI passed; latest-head/integration gates pending  
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
| Phase 6A — typed research-planning task contracts | INTEGRATION PENDING | PR #16 |

## Phase 6A — typed research-planning task contracts

**Branch:** `phase/6a-planning-task-contracts`  
**Integration carrier:** PR #16  
**Initial PR CI:** `33703967034` — success

### Implemented

- added stable `ptask-*` PlanningTask identity and shared validator;
- added framework-neutral `PlanningTask`, `PlanningTaskScope`, `PlanningReference`, task kind/status/priority enums, and authorization requirement;
- required every task to declare one bounded objective and at least one completion criterion;
- added typed references to ResearchQuestion, Hypothesis, Claim, Evidence, Artifact, Citation, LiteratureNote, Experiment, and ExperimentRun IDs;
- added typed task dependencies with duplicate and direct self-dependency rejection;
- separated operational task lifecycle from scientific approval;
- required completed tasks to carry durable typed completion references and forbade completion references on non-completed tasks;
- reused canonical human `Decision` records by extending `DecisionSubjectType` with `planning_task`;
- required human-gated tasks to carry a Decision before entering execution-eligible states;
- hard-gated `experiment_execution` tasks to `authorization_requirement=human`, required a concrete Experiment reference, and required an ExperimentRun completion reference when completed;
- kept blocked/cancelled operational states usable before or after authorization without treating them as scientific decisions;
- added Draft 2020-12 `schemas/planning-task.schema.json` and extended the research-state Decision schema for `planning_task` subjects;
- kept standard JSON Schema only: direct self-dependency value comparison remains a Python/domain invariant rather than using non-standard `$data` extensions;
- exported all planning contracts from the package root;
- added positive/negative Python and JSON Schema tests, including a regression that Phase 2 registry defers planning-task Decision resolution to the Phase 6 domain;
- documented the contract in `docs/PLANNING_TASK_CONTRACTS.md`;
- recorded durable decisions in `docs/decisions/ADR-0015-bounded-planning-tasks-and-human-authorization.md`.

### Authority boundary

PlanningTask status is operational only.

`completed` does **not** mean:

- a ResearchQuestion is resolved;
- a Hypothesis is accepted;
- a Claim is approved;
- Evidence supports/contradicts a Claim;
- an experiment is scientifically valid;
- reproduction succeeded;
- manuscript text is approved.

`priority` and `rationale` are proposal metadata rather than scientific truth. A PlanningTask is not itself an execution capability token; future executors must still enforce authorization and bounded-work policy.

### Validation and scope audit

- `main..phase/6a-planning-task-contracts` is ahead-only and limited to planning contracts, shared ID/Decision schema integration, exports, tests, documentation/ADR, and this canonical handoff;
- initial PR #16 CI run `33703967034` completed successfully, including all existing Phase 1–5C tests and the new Phase 6A suite;
- no planning registry, scheduler, worker, autonomous loop, provider-specific framework, experiment execution, scientific approval automation, manuscript generation, or submission automation was introduced.

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
- [x] initial PR CI passes;
- [ ] latest-head PR CI passes after this handoff update;
- [ ] PR #16 merged and `main` push CI passes.

## Next bounded increment — Phase 6B: repository planning-task registry and authorization/dependency audit

**Status:** BLOCKED until Phase 6A integration is complete.

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
