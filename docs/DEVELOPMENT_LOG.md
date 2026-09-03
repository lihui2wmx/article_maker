# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-03

**Active phase:** Phase 6B — repository planning-task registry and authorization/dependency audit  
**Status:** IMPLEMENTED — PR #17 initial CI passed; latest-head/integration gates pending  
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
| Phase 6B — PlanningTask registry/authorization audit | INTEGRATION PENDING | PR #17 |

## Phase 6B — repository PlanningTask registry and audit

**Branch:** `phase/6b-planning-task-registry`  
**Integration carrier:** PR #17  
**Initial passing PR CI:** `33705460686` — success

### Implemented

- canonical `research/planning_tasks/<ptask-id>.json` repository layout;
- deterministic newline-terminated canonical JSON persistence with atomic replacement;
- deterministic `save`, `load`, and `list` APIs;
- malformed-record-tolerant audit with filename/ID and duplicate-ID checks;
- typed PlanningReference resolution against Phase 1–5 ResearchQuestion, Hypothesis, Claim, Evidence, Artifact, Citation, LiteratureNote, Experiment, and ExperimentRun state;
- repository-level missing dependency detection and transitive dependency-cycle detection;
- human governing Decision existence, subject/backlink, and outcome consistency checks;
- completed-task completion-reference resolution;
- read-only audit behavior with no scheduling or execution side effects;
- package-root exports and focused regression tests;
- canonical layout update in `docs/ARCHITECTURE.md`;
- operational contract documentation in `docs/PLANNING_TASK_REGISTRY.md`.

The first PR test attempts failed because the new test fixture used the non-canonical Claim ID prefix `claim-`; the fixture was corrected to canonical `clm-`. Run `33705460686` then passed the complete repository test suite.

### Authority boundary

PlanningTask persistence and audit remain operational repository integrity mechanisms. A clean audit or `completed` task does not approve a Claim, accept a Hypothesis, interpret Evidence, establish experiment validity/reproducibility, approve manuscript text, select a venue, or authorize submission.

### Phase 6B exit conditions

- [x] canonical PlanningTask repository location exists;
- [x] deterministic save/load/list APIs exist;
- [x] malformed PlanningTask records do not abort audit;
- [x] filename/ID and duplicate-ID integrity checks exist;
- [x] every Phase 6A PlanningReference type resolves against canonical Phase 1–5 state;
- [x] missing dependencies and transitive dependency cycles are audited;
- [x] human governing Decisions are resolved and checked for subject/backlink consistency;
- [x] approve/reject/supersede outcomes are checked against PlanningTask authorization lifecycle;
- [x] completion references are resolved;
- [x] audit is read-only and does not schedule or execute work;
- [x] architecture and registry documentation are updated;
- [x] initial passing PR CI exists (`33705460686`);
- [ ] latest-head PR CI passes after this canonical handoff update;
- [ ] PR #17 merged and merged-main CI passes.

### Non-goals preserved

Phase 6B does not introduce autonomous agent loops, task scheduling/workers, provider-specific agent frameworks, experiment execution, automatic scientific approval, manuscript generation, or submission automation.

## Next bounded increment after Phase 6B integration

Do not activate the next Phase 6 increment until PR #17 is integrated and merged-main CI passes. The next increment should remain bounded to research-planning proposal construction over audited repository state; it must propose PlanningTasks rather than schedule or execute them, and human scientific authority gates remain unchanged.
