# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-03

**Active phase:** Phase 6C — bounded research-planning proposal construction from audited repository state  
**Status:** IMPLEMENTED — integration review/merge pending  
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
| Phase 6C — deterministic PlanningTask proposals | INTEGRATION PENDING | PR #18 |

## Phase 6C — bounded research-planning proposal construction

**Branch:** `phase/6c-planning-proposals`  
**Integration carrier:** PR #18  
**Initial PR CI:** `33705962043` — success  
**Closure code/test CI:** `33768609934` — success

### Implemented

- framework-neutral `PlanningProposalCandidate`, `PlanningProposalReason`, and `PlanningProposalBuilder`;
- pure deterministic `propose_from_state()` over already-audited canonical objects;
- repository-backed `propose_from_repository()` that blocks structural audit errors while preserving advisory warnings as usable planning state;
- stable proposal IDs derived from `(proposal_reason, source_id)`;
- rule-based proposal for active Claims with no persisted ClaimEvidenceLink -> `evidence_review`;
- rule-based proposal for Citations with no LiteratureNote -> `literature_analysis`;
- rule-based proposal for Experiments with no completed ExperimentRun -> human-gated `experiment_execution`;
- rejected/superseded Claims excluded from new evidence-review proposals;
- existing deterministic PlanningTask IDs suppress duplicate proposals;
- explicit proposal provenance in task metadata and attributed `rule-based-planner` proposer;
- package-root exports for the public Phase 6C proposal API;
- focused tests for determinism, resolved-gap suppression, inactive-Claim suppression, duplicate suppression, human gating, package exports, advisory-warning passage, and dirty-audit refusal/read-only behavior;
- operational documentation in `docs/PLANNING_PROPOSALS.md`.

### AI-native repository correction

The human researcher clarified the intended final product boundary during Phase 6C closure: `article_maker` is to be handed directly to an AI agent, which reads and operates the repository to perform scientific/manuscript work. The repository is not intended to call AI models through LLM/provider APIs as part of its core runtime.

This correction is now durable in:

- `PROJECT.md`;
- `docs/ARCHITECTURE.md`;
- `docs/decisions/ADR-0016-ai-native-repository-execution-model.md`.

The canonical execution direction is **AI operates repository**, not **repository calls AI**. Core development should prioritize agent-legible instructions, deterministic repository tooling, explicit state, provenance, reviewable transitions, and resumable handoff. Do not introduce model/provider SDKs or embedded agent-framework runtimes as core product dependencies.

### Authority boundary

Phase 6C identifies objective missing repository structure only. It does not decide whether evidence is scientifically sufficient, establish novelty, choose research direction, persist proposals as accepted work, schedule tasks, execute experiments, approve Claims/Hypotheses/Evidence interpretations, generate manuscripts, or submit externally.

Experiment-execution candidates remain `status=proposed`, `authorization_requirement=human`, and have no governing Decision. They cannot become execution-eligible under the Phase 6A/6B contract without later explicit human authorization.

### Closure checklist

- [x] deterministic proposal input/output layer exists;
- [x] structural repository audit gate precedes repository-backed proposals;
- [x] advisory audit warnings do not incorrectly block planning;
- [x] initial objective structural-gap rules exist;
- [x] proposal/persistence/execution boundaries remain separate;
- [x] experiment-execution proposals preserve hard human authorization;
- [x] deterministic tests exist;
- [x] proposal contract documentation exists;
- [x] package-root exports are added for the new public proposal API;
- [x] bounded diff review completed and warning-gate defect corrected;
- [x] AI-native repository execution model is documented as ADR-0016;
- [x] closure code/test CI passes (`33768609934`);
- [ ] PR #18 is marked ready/reviewed and merged;
- [ ] merged-main CI passes.

## Next bounded task

Complete PR #18 integration only: verify final handoff-head CI, mark the PR ready for review, merge after gates are green, verify merged-main CI, then update this log to close Phase 6C and activate the next bounded phase. Do not add provider/model API integration, embedded agent runtimes, automatic proposal persistence, scheduling, workers, or execution in this closure increment.
