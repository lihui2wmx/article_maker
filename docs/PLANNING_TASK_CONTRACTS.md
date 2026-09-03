# Planning Task Contracts

## Purpose

Phase 6A introduces framework-neutral contracts for bounded research-planning work. A `PlanningTask` records proposed work that a human or agent may perform against canonical repository state.

A task is an operational object. It is not a scientific claim, scientific approval, manuscript instruction, or autonomous-agent command.

## Core objects

### `PlanningTask`

Stable identity:

```text
ptask-*
```

A task records:

- task kind;
- operational status;
- explicit bounded scope;
- proposer attribution;
- priority and rationale;
- typed references to canonical research state;
- dependencies on other planning tasks;
- whether human authorization is required;
- governing human Decision where required;
- typed completion references after completion;
- JSON-only metadata.

### `PlanningTaskScope`

Every task must state:

- one nonblank `objective`;
- at least one `completion_criteria` entry;
- optional `constraints`;
- optional `non_goals`.

This is the contract-level boundary against open-ended requests such as "research this until satisfied". Phase 6A does not define agent iteration mechanics; it defines what must be true for work to be considered bounded and reviewable.

### `PlanningReference`

References are typed rather than free-form strings. Supported reference types are:

- `research_question` -> `rq-*`;
- `hypothesis` -> `hyp-*`;
- `claim` -> `clm-*`;
- `evidence` -> `ev-*`;
- `artifact` -> `art-*`;
- `citation` -> `cit-*`;
- `literature_note` -> `litn-*`;
- `experiment` -> `exp-*`;
- `experiment_run` -> `exprun-*`.

Object-level validation checks ID grammar only. Repository-level existence and relationship resolution are deferred to Phase 6B.

## Task kinds

Phase 6A defines:

```text
literature_search
literature_analysis
experiment_design
experiment_execution
data_analysis
theory_analysis
evidence_review
claim_review
reproducibility_check
citation_audit
other
```

Task kind classifies proposed work. It does not grant capabilities by itself.

## Operational lifecycle

Task states are:

```text
proposed
ready
in_progress
blocked
completed
cancelled
rejected
```

These states describe workflow progress only.

In particular:

```text
PlanningTask.status = completed
```

means the declared work and completion criteria were carried out with completion references recorded. It does **not** mean:

- a ResearchQuestion is resolved;
- a Hypothesis is accepted;
- a Claim is approved;
- Evidence supports or contradicts a Claim;
- an experiment is scientifically valid;
- a reproduction succeeded;
- manuscript text is approved.

Those conclusions remain in their own governed scientific state.

## Human authorization

`authorization_requirement` is either:

```text
none
human
```

For `none` tasks:

- no `governing_decision_id` is allowed;
- `rejected` is not a valid state because there is no human authorization gate to reject.

For `human` tasks:

- `proposed` must not already carry a Decision;
- `ready`, `in_progress`, and `completed` require a `governing_decision_id`;
- `rejected` requires a `governing_decision_id`;
- `blocked` and `cancelled` may exist before or after authorization, so they may carry a Decision or not.

The referenced Decision remains a human-authority `Decision` record. Phase 6A extends `DecisionSubjectType` with:

```text
planning_task
```

A Decision with that subject must use a valid `ptask-*` subject ID.

Phase 6A validates the identifier relationship only. It does not yet resolve the Decision file, verify the Decision outcome against task state, or validate Decision-history heads. Those are Phase 6B repository concerns.

## Experiment execution is always human-gated

`experiment_execution` is treated as an explicitly high-impact task kind in v1.

It must:

1. declare `authorization_requirement=human`;
2. reference at least one concrete `Experiment`;
3. carry a human Decision before entering `ready`, `in_progress`, or `completed`;
4. include at least one `ExperimentRun` completion reference when completed.

This contract does not execute the Experiment. It only prevents a proposed experiment-execution task from being represented as an ungated generic work item.

## Dependencies

`depends_on_task_ids` contains stable `ptask-*` references.

Object-level validation rejects:

- invalid planning-task IDs;
- duplicates;
- direct self-dependency.

Transitive missing dependencies and cycles require repository-wide state and are deferred to Phase 6B.

The direct self-dependency invariant is enforced by the Python domain model. Standard JSON Schema Draft 2020-12 cannot compare one instance value with another arbitrary instance value without non-standard extensions, so the JSON Schema intentionally does not pretend to express that comparison.

## Completion references

`completion_refs` are permitted only when `status=completed` and at least one is required in that state.

Completion references identify durable output or completion state. Examples include:

- an Artifact produced by an analysis task;
- an Evidence record produced by an evidence task;
- a Citation/LiteratureNote from literature work;
- an ExperimentRun from experiment execution.

Completion references are operational provenance. They do not convert the referenced object into approved scientific truth.

## Proposal metadata is not scientific truth

`priority` and `rationale` are planning metadata. An agent may propose that a task is urgent or important, but these fields do not alter Claim, Hypothesis, Evidence, or Decision state.

## Schema and implementation

Canonical external contract:

```text
schemas/planning-task.schema.json
```

Python implementation:

```text
src/article_maker/planning.py
```

The schema uses JSON Schema Draft 2020-12. Python adds domain invariants that cannot be expressed portably in standard JSON Schema, such as direct self-dependency comparison.

## Phase 6A non-goals

Phase 6A does not add:

- a planning-task repository registry;
- repository-level reference resolution;
- dependency-cycle audit;
- autonomous agent loops;
- task scheduling or worker execution;
- provider-specific agent frameworks;
- automatic Experiment execution;
- automatic scientific approval;
- Claim/Evidence interpretation;
- manuscript generation;
- submission automation.
