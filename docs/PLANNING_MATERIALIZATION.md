# Reviewed PlanningProposal Materialization

## Purpose

Phase 6D provides the repository-native bridge from advisory Phase 6C proposal candidates to durable canonical `PlanningTask` state. An external AI operator may inspect proposal candidates and present a subset for review, but no candidate is written merely because it was generated.

Materialization is a reviewed state transition, not scheduling or execution.

## Workflow

The intended operator flow is:

```text
current audited repository state
  -> Phase 6C deterministic proposal candidates
  -> explicit PlanningTask-ID selection
  -> dry-run PlanningMaterializationPlan
  -> human/operator review of exact task previews + plan digest
  -> execute with reviewed digest
  -> recompute current candidates
  -> stale/tamper/conflict checks
  -> exact PlanningTask writes
  -> reload verification + PlanningTask audit
```

`PlanningProposalMaterializer.plan()` is read-only. It requires one or more explicit `PlanningMaterializationSelection` values and returns only selected candidates, deterministically sorted by PlanningTask ID.

## Review binding

Every `PlannedPlanningTask` preserves:

- the Phase 6C `proposal_reason`;
- the canonical proposal `source_id`;
- a digest of the exact deterministic proposal candidate;
- the complete `PlanningTask` preview that would be persisted.

`planning_materialization_plan_digest()` binds the complete reviewed plan. `execute()` requires the caller to provide that exact digest.

Execution deep-copies the reviewed plan, recomputes current repository proposals, and requires every selected candidate to remain available with the same reason, source, digest, and complete PlanningTask preview. A changed or resolved source gap therefore invalidates the reviewed plan instead of silently changing what is written.

## Conflict and post-write behavior

An existing PlanningTask ID is a conflict. Materialization never overwrites it silently.

After writes, every new task is reloaded and compared with the reviewed preview. The PlanningTask registry audit must remain clean. Newly written files are removed on in-process write/post-write failure so a failed materialization does not intentionally leave a partial reviewed batch.

## Human authority

Materialization records a bounded work item only. It does not approve the scientific action represented by that work item.

In particular, Phase 6C experiment-execution candidates retain:

- `status=proposed`;
- `authorization_requirement=human`;
- no `governing_decision_id`.

Materializing such a candidate therefore does **not** authorize experiment execution. A later explicit human Decision remains required under the Phase 6A/6B contract before the task can enter execution-eligible lifecycle states.

Likewise, materialization does not approve Claims, accept Hypotheses, interpret ambiguous Evidence, assert novelty, select a venue, approve manuscript content, or authorize submission.

## AI-native boundary

This module is deterministic repository tooling for an external AI operator. It performs no model call and needs no provider API. The AI reads the repository, proposes and reviews repository-native state transitions, invokes deterministic tools, and leaves durable state for subsequent AI/human operators.

## Non-goals

Phase 6D does not introduce:

- automatic materialization of all proposals;
- implicit approval from proposal generation;
- scheduling or workers;
- experiment execution;
- LLM/provider API integration or embedded agent frameworks;
- probabilistic proposal ranking;
- manuscript generation or submission automation.
