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
**Status:** IMPLEMENTED — initial PR CI passed; package exports/latest-head integration gates pending  
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

### Implemented

- framework-neutral `PlanningProposalCandidate`, `PlanningProposalReason`, and `PlanningProposalBuilder`;
- pure deterministic `propose_from_state()` over already-audited canonical objects;
- repository-backed `propose_from_repository()` that refuses to operate when Claim/Evidence, literature, experiment, or PlanningTask audits report findings;
- stable proposal IDs derived from `(proposal_reason, source_id)`;
- rule-based proposal for active Claims with no persisted ClaimEvidenceLink -> `evidence_review`;
- rule-based proposal for Citations with no LiteratureNote -> `literature_analysis`;
- rule-based proposal for Experiments with no completed ExperimentRun -> human-gated `experiment_execution`;
- rejected/superseded Claims excluded from new evidence-review proposals;
- existing deterministic PlanningTask IDs suppress duplicate proposals;
- explicit proposal provenance in task metadata and attributed `rule-based-planner` proposer;
- focused tests for determinism, resolved-gap suppression, inactive-Claim suppression, duplicate suppression, human gating, and dirty-audit refusal/read-only behavior;
- operational documentation in `docs/PLANNING_PROPOSALS.md`.

### Authority boundary

Phase 6C identifies objective missing repository structure only. It does not decide whether evidence is scientifically sufficient, establish novelty, choose research direction, persist proposals as accepted work, schedule tasks, execute experiments, approve Claims/Hypotheses/Evidence interpretations, generate manuscripts, or submit externally.

Experiment-execution candidates remain `status=proposed`, `authorization_requirement=human`, and have no governing Decision. They cannot become execution-eligible under the Phase 6A/6B contract without later explicit human authorization.

### Remaining closure work

- [x] deterministic proposal input/output layer exists;
- [x] repository audit gate precedes repository-backed proposals;
- [x] initial objective structural-gap rules exist;
- [x] proposal/persistence/execution boundaries remain separate;
- [x] experiment-execution proposals preserve hard human authorization;
- [x] deterministic tests exist and initial PR CI passes (`33705962043`);
- [x] proposal contract documentation exists;
- [ ] package-root exports are added for the new public proposal API;
- [ ] latest-head PR CI passes after closure updates;
- [ ] PR #18 is reviewed/merged and merged-main CI passes.

## Next bounded task

Add package-root exports for the Phase 6C public proposal API, perform a bounded PR diff review, update PR #18 validation metadata, and run latest-head CI. Do not add probabilistic model/provider adapters, automatic proposal persistence, scheduling, workers, or execution in this closure increment.
