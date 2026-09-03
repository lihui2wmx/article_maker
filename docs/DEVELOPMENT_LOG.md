# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-03

**Active phase:** Phase 6D — reviewed PlanningProposal materialization into canonical PlanningTask state  
**Status:** IMPLEMENTED — latest-head integration gates pending  
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
| Phase 6B — PlanningTask registry/authorization audit | COMPLETE | PR #17 |
| Phase 6C — deterministic PlanningTask proposals | COMPLETE | PR #18 |
| Phase 6D — reviewed PlanningProposal materialization | INTEGRATION PENDING | PR #19 |

## AI-native repository product boundary

`article_maker` is handed directly to an AI agent, which reads and operates the repository to perform research and manuscript work. The canonical execution direction is **AI operates repository**, not **repository calls AI**.

This boundary is durable in `PROJECT.md`, `docs/ARCHITECTURE.md`, and `docs/decisions/ADR-0016-ai-native-repository-execution-model.md`. Core development must prioritize agent-legible repository instructions, deterministic tools, explicit canonical state, provenance, reviewable transitions, and resumable handoff. Model/provider SDKs and embedded agent frameworks are not planned core dependencies.

## Phase 6D — reviewed PlanningProposal materialization

**Branch:** `phase/6d-planning-proposal-materialization`  
**Integration carrier:** PR #19  
**Initial PR CI:** `33769359626` — success  
**Bounded-review fix CI:** `33769482936` — success

### Implemented

- `PlanningProposalMaterializer` as a repository-native deterministic bridge from Phase 6C candidates to Phase 6B canonical `PlanningTask` state;
- explicit `PlanningMaterializationSelection` by deterministic PlanningTask identity;
- read-only dry-run `PlanningMaterializationPlan` construction;
- exact `PlanningTask` previews plus proposal reason/source binding;
- deterministic candidate and whole-plan digests;
- execution bound to an explicitly reviewed digest;
- current repository proposal recomputation before writes;
- stale proposal, preview tamper, and existing-task conflict rejection;
- exact PlanningTask persistence and reload equality verification;
- post-write PlanningTask audit plus best-effort rollback of newly written records on in-process failure;
- preservation of Phase 6A/6C authorization semantics, especially proposed human-gated experiment execution;
- public package-root exports;
- `docs/PLANNING_MATERIALIZATION.md` and ADR-0017;
- focused tests for explicit selection/read-only planning, deterministic subsets, review digest binding, stale/tamper rejection, conflicts, exact persistence, human-gate preservation, post-write rollback, duplicate reviewed-plan entries, and package exports.

### Bounded review finding

Integration review found that a caller could manually construct a `PlanningMaterializationPlan` containing the same PlanningTask identity more than once even though `plan()` itself never emits duplicates. Without execution-time plan-integrity checks, such a manually constructed reviewed plan could write the same task twice in one batch. Execution now rejects duplicate PlanningTask IDs and duplicate `(proposal_reason, source_id)` sources before repository mutation.

### Authority boundary

Materialization records bounded work state only. It does not approve the scientific action represented by a task. In particular, materializing an `experiment_execution` proposal leaves it `status=proposed`, `authorization_requirement=human`, with no governing Decision; later explicit human authorization is still required before it can become execution-eligible.

Materialization does not approve Claims, accept Hypotheses, interpret ambiguous Evidence, assert novelty, schedule or execute work, select a venue, approve manuscript content, or authorize submission.

### Phase 6D closure checklist

- [x] explicit proposal selection is required before writes;
- [x] planning is read-only and deterministic;
- [x] exact proposal/source/task previews are digest-bound;
- [x] execution recomputes current proposals and rejects stale/tampered state;
- [x] existing PlanningTask conflicts are rejected;
- [x] duplicate manually constructed reviewed-plan entries are rejected;
- [x] only exact reviewed PlanningTask previews are persisted;
- [x] post-write reload/audit and rollback behavior exist;
- [x] human authorization semantics are preserved;
- [x] package-root exports, tests, documentation, and ADR exist;
- [x] initial PR CI passes (`33769359626`);
- [x] bounded-review fix CI passes (`33769482936`);
- [ ] latest-head CI passes after package exports/handoff update;
- [ ] PR #19 is marked ready/reviewed and merged;
- [ ] merged-main CI passes.

## Next bounded task

Complete Phase 6D integration only: verify latest-head CI after package exports and canonical handoff updates, perform a final bounded PR diff review, update PR #19 validation metadata, mark it ready, merge after gates are green, verify merged-main CI, then close Phase 6D and activate the next bounded phase. Do not add scheduling, workers, task execution, model/provider API integration, embedded agent runtimes, manuscript generation, or submission automation in this closure increment.
