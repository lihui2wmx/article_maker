# ADR-0015: Bounded planning tasks and human authorization

- **Status:** Accepted
- **Date:** 2026-09-03
- **Phase:** 6A

## Context

The repository now contains typed artifacts, research questions and hypotheses, a governed Claim/Evidence graph, literature state, and Experiment provenance. The next layer needs to represent work that agents may recommend or carry out without turning an agent recommendation into scientific authority or an unbounded autonomous loop.

A generic free-form todo string is insufficient because it does not express:

- what canonical state the task concerns;
- what work is in or out of scope;
- how completion is evidenced;
- whether human authorization is required;
- whether the task depends on other work;
- whether completion has any scientific meaning.

At the same time, Phase 6A must not introduce an agent framework, scheduler, runner, or automatic scientific approval system.

## Decision

### 1. Planning tasks are canonical typed proposals

Introduce `PlanningTask` with stable `ptask-*` identity.

A task has an explicit kind, operational lifecycle, bounded scope, proposer, priority/rationale, typed canonical references, task dependencies, authorization requirement, optional governing human Decision, completion references, and JSON metadata.

### 2. Bounded scope is explicit data

Every task contains `PlanningTaskScope` with:

- one objective;
- at least one completion criterion;
- optional constraints;
- optional non-goals.

The contract does not encode a provider/framework-specific iteration loop. It encodes the conditions needed for another actor to know what bounded work was proposed and when it can stop.

### 3. Task lifecycle is operational, not scientific

The v1 task lifecycle is:

```text
proposed
ready
in_progress
blocked
completed
cancelled
rejected
```

`completed` means the work item completed and produced durable completion references. It does not accept a Hypothesis, approve a Claim, establish Evidence interpretation, prove reproduction success, or approve manuscript text.

### 4. Canonical references are typed

Planning references use explicit reference type + stable internal ID rather than arbitrary paths or prose identifiers.

Phase 6A supports references to ResearchQuestion, Hypothesis, Claim, Evidence, Artifact, Citation, LiteratureNote, Experiment, and ExperimentRun.

Repository existence and cross-object semantic checks remain Phase 6B responsibilities.

### 5. Human authorization reuses `Decision`

Do not create a second approval-record type.

Extend `DecisionSubjectType` with `planning_task`. A human-gated task refers to the same canonical human Decision infrastructure already used by scientific-state governance.

This does not make PlanningTask a scientific state object. It only reuses the auditable human-authority record for task authorization.

### 6. High-impact experiment execution is always human-gated

A task with kind `experiment_execution` must:

- require human authorization;
- reference a concrete Experiment;
- have a governing Decision before it becomes ready/in-progress/completed;
- reference an ExperimentRun when completed.

The task contract never executes the Experiment itself.

### 7. Completion requires durable references

A completed task must contain at least one typed `completion_ref`. Non-completed tasks may not contain completion references.

This makes task completion auditable while avoiding any implication that the completion object is scientifically approved.

### 8. Dependencies are task identities, not execution control

`depends_on_task_ids` references `ptask-*` identities. Phase 6A rejects invalid IDs, duplicates, and direct self-dependency.

Missing dependencies, transitive cycles, authorization Decision resolution, and completion-reference existence require repository state and are deferred to Phase 6B.

### 9. Use standard Draft 2020-12 only

`schemas/planning-task.schema.json` remains standard JSON Schema Draft 2020-12.

Do not introduce non-standard `$data`-style instance-comparison extensions to express self-dependency. The Python domain model enforces that invariant; repository-level graph audit will enforce dependency integrity in Phase 6B.

## Consequences

### Positive

- Agents can propose bounded work without gaining authority to approve science.
- High-impact experiment execution has an explicit human gate before any future runner is connected.
- Completion is tied to durable repository state.
- Planning tasks can later be persisted, audited, scheduled, and assigned without changing the core domain contract.
- Provider/framework choice remains an adapter concern.

### Costs

- Some invariants cannot be completely expressed in portable JSON Schema and need domain/repository validation.
- Phase 6B is required before planning-task references and Decision backlinks are repository-verified.
- A future executor must still implement capability checks; `PlanningTask` alone is not an execution authorization token.

## Rejected alternatives

### Free-form todo files

Rejected because they cannot reliably encode authority, dependencies, canonical references, or completion provenance.

### Let task kind imply permission

Rejected. Task kind is classification, not a capability grant. An explicit authorization field and human Decision are required for high-impact work.

### Create a separate `TaskApproval` object

Rejected because it would duplicate the existing human `Decision` audit trail and create two competing sources of approval truth.

### Treat task completion as scientific acceptance

Rejected because operational completion and scientific truth are separate state machines.

### Introduce an agent framework now

Rejected because Phase 6A is a domain-contract phase. LangChain/CrewAI/AutoGen/provider-specific execution concerns remain adapters for later phases.
