# ADR-0017 — Reviewed PlanningProposal materialization

## Status

Accepted — 2026-09-03

## Context

Phase 6C can deterministically identify bounded research-work candidates from audited repository gaps, while Phase 6B can persist canonical `PlanningTask` records. Directly saving every generated candidate would collapse advisory planning into automatic work acceptance and would make it difficult for an external AI operator or human researcher to review the exact state transition before it becomes durable.

The project already uses reviewed dry-run plans, exact digest binding, stale-source checks, conflict rejection, and post-write verification for other repository bridges.

## Decision

The transition from a Phase 6C proposal candidate to canonical `PlanningTask` state is an explicit reviewed materialization step.

A materialization plan must contain the exact selected candidate identities and complete PlanningTask previews. The plan has a deterministic digest. Execution requires that exact reviewed digest and must recompute current proposal state before writing. If a selected proposal disappeared, changed, became occupied, or no longer deterministically produces the reviewed task preview, execution fails rather than adapting the plan silently.

Only explicitly selected candidates are written. Planning itself is read-only. Existing PlanningTask identities are conflicts and are never silently overwritten. Persisted tasks are reloaded and audited; newly written files are rolled back on in-process post-write failure where practical.

Materialization preserves the candidate's authorization semantics exactly. In particular, a proposed human-gated experiment-execution task remains unauthorized after materialization until a separate human Decision permits the relevant lifecycle transition.

## Consequences

- External AI operators can present a concrete dry-run work-state change for review before mutating canonical state.
- Proposal generation and durable work acceptance remain separate operations.
- Repository drift between review and execution is detected deterministically.
- Human scientific authority is preserved because materialization records work, not scientific approval or execution authorization.
- The mechanism is provider-independent repository tooling and requires no embedded model runtime.

## Non-goals

This decision does not define task scheduling, worker execution, automatic research-direction approval, experiment execution, manuscript writing, or model/provider integration.
