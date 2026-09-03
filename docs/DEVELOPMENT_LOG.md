# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-03

**Active next phase:** Phase 6D — reviewed PlanningProposal materialization into canonical PlanningTask state  
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
| Phase 6B — PlanningTask registry/authorization audit | COMPLETE | PR #17 |
| Phase 6C — deterministic PlanningTask proposals | COMPLETE | PR #18 |

## Phase 6C closure

**Branch:** `phase/6c-planning-proposals`  
**Integration carrier:** PR #18  
**Initial PR CI:** `33705962043` — success  
**Closure code/test CI:** `33768609934` — success  
**Final handoff-head CI:** `33768731200` — success  
**Integrated main commit:** `1d4f023d4f7cc3f7dba96dae34c54dafd0b9624e`

Phase 6C added:

- framework-neutral `PlanningProposalCandidate`, `PlanningProposalReason`, and `PlanningProposalBuilder`;
- pure deterministic `propose_from_state()` over already-audited canonical objects;
- repository-backed `propose_from_repository()` that blocks structural audit errors while preserving advisory warnings as usable planning state;
- stable proposal IDs derived from `(proposal_reason, source_id)`;
- objective structural-gap proposals for unlinked active Claims, unnoted Citations, and Experiments without completed runs;
- hard human authorization for experiment-execution candidates;
- duplicate suppression against existing deterministic PlanningTask IDs;
- package-root exports and focused regression tests;
- `docs/PLANNING_PROPOSALS.md`;
- the bounded-review correction that advisory warnings must not be treated as structural errors.

### AI-native repository architecture correction

During Phase 6C closure, the human researcher clarified the final product boundary: `article_maker` is intended to be handed directly to an AI agent, which reads and operates the repository to perform research and manuscript work. The repository is not intended to invoke AI through LLM/provider APIs as part of its core product runtime.

This is now canonical in `PROJECT.md`, `docs/ARCHITECTURE.md`, and `docs/decisions/ADR-0016-ai-native-repository-execution-model.md`.

The execution direction is **AI operates repository**, not **repository calls AI**. Future development should prioritize agent-legible repository instructions, deterministic tools, explicit canonical state, provenance, reviewable transitions, and resumable handoff. Model/provider SDKs and embedded agent frameworks are not planned core dependencies.

### Phase 6C exit conditions

- [x] deterministic proposal input/output layer exists;
- [x] structural repository audit gate precedes repository-backed proposals;
- [x] advisory audit warnings remain available to planning rather than blocking it;
- [x] initial objective structural-gap rules exist;
- [x] proposal/persistence/execution boundaries remain separate;
- [x] experiment-execution proposals preserve hard human authorization;
- [x] deterministic tests and package-root exports exist;
- [x] proposal documentation and AI-native architecture ADR exist;
- [x] bounded diff review completed;
- [x] final PR-head CI passes (`33768731200`);
- [x] PR #18 squash merged (`1d4f023d4f7cc3f7dba96dae34c54dafd0b9624e`).

## Next bounded increment — Phase 6D: reviewed PlanningProposal materialization

**Status:** READY after Phase 6C integration.

### Objective

Provide a deterministic, review-bound path by which an external AI operator can present Phase 6C proposal candidates for explicit selection and then materialize only the reviewed selections into canonical `PlanningTask` repository state. This bridges advisory proposal construction to durable work state without scheduling or executing work.

### Initial boundary

Phase 6D should at minimum:

- consume deterministic Phase 6C proposal candidates from current audited repository state;
- build a reviewable selection/materialization plan containing exact candidate identities, task previews, source-state binding, and a stable digest;
- require explicit selection before any PlanningTask write;
- re-audit/recompute source proposals at execution time and reject stale or tampered plans;
- persist only exact reviewed PlanningTask previews through the existing Phase 6B registry;
- reject conflicts rather than silently overwrite existing PlanningTask records;
- preserve existing human authorization requirements, especially for experiment execution;
- verify persisted records and run post-write PlanningTask audit;
- remain directly usable by an external AI operator through repository-native Python/CLI surfaces rather than any model/provider API.

### Human authority boundary

Materializing a candidate records bounded work state; it does not itself approve a scientific Claim, accept a Hypothesis, interpret ambiguous Evidence, assert novelty, authorize an experiment execution task, choose a venue, approve manuscript content, or authorize submission. Where a selected task changes scientific direction or requires a human gate under existing contracts, the corresponding human Decision remains separately required.

### Non-goals

Do not introduce in Phase 6D:

- LLM/provider API integrations or model SDKs;
- embedded autonomous-agent frameworks;
- automatic acceptance of every proposal;
- scheduling, workers, or execution;
- experiment execution;
- probabilistic proposal ranking;
- automatic scientific approval or novelty assertions;
- manuscript generation or submission automation.
