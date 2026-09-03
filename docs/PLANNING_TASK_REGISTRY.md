# PlanningTask Registry and Audit

## Purpose

Phase 6B persists Phase 6A `PlanningTask` contracts as canonical repository state and provides a deterministic, read-only integrity audit. The registry does not schedule, execute, prioritize automatically, or grant scientific authority.

## Canonical layout

Planning tasks are stored at:

```text
research/planning_tasks/<planning-task-id>.json
```

Each filename must match the record's canonical `ptask-*` identifier. JSON serialization is deterministic, UTF-8, sorted by key, indented, and newline-terminated.

## Registry API

`PlanningTaskRegistry` provides:

- `save(task)` — atomically persist one validated PlanningTask;
- `load(planning_task_id)` — load one canonical record;
- `list()` — return records in deterministic filename order;
- `audit()` — inspect repository integrity without writing or executing work.

Registry paths must remain repository-relative and may not traverse outside the repository root.

## Audit boundary

The Phase 6B audit reports repository-level integrity failures while continuing past malformed PlanningTask records.

It checks:

1. parse/validation failures;
2. filename/ID mismatches and duplicate IDs;
3. missing `depends_on_task_ids` targets;
4. direct or transitive dependency cycles represented in persisted repository state;
5. all typed task references against the corresponding Phase 1–5 canonical registry;
6. completed-task `completion_refs` against canonical repository state;
7. human `governing_decision_id` existence and validity;
8. governing Decision subject type and backlink to the PlanningTask;
9. Decision outcome consistency with PlanningTask authorization state.

`ExperimentRun` references are resolved by durable run identity across canonical `experiments/<exp-id>/runs/*.json` records. Malformed ExperimentRun records are ignored as resolution candidates and therefore cannot satisfy a PlanningTask reference.

## Human authorization semantics

For `authorization_requirement=human`, Phase 6B reuses the canonical `Decision` object.

- `approve` may govern execution-eligible states (`ready`, `in_progress`, `completed`) and may remain attached if a task later becomes operationally `blocked` or `cancelled`.
- `reject` is consistent only with task status `rejected`.
- `supersede` is not an authorization transition in the current PlanningTask lifecycle and is reported as inconsistent.

This audit verifies repository consistency only. It does not infer scientific approval from operational task state.

## Read-only guarantee

`audit()` must not:

- mutate PlanningTask records;
- create Decisions;
- alter dependencies;
- schedule work;
- execute experiments or analyses;
- change scientific state;
- approve Claims, Hypotheses, Evidence interpretations, manuscripts, venues, or submissions.

## Non-goals

Phase 6B deliberately excludes schedulers, workers, autonomous agent loops, provider-specific agent frameworks, execution capability tokens, experiment execution, automatic scientific approval, manuscript generation, and submission automation.
