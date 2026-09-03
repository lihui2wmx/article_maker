# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-03

**Active next phase:** Phase 6C — bounded research-planning proposal construction from audited repository state  
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

## Phase 6B closure

**Branch:** `phase/6b-planning-task-registry`  
**Integration carrier:** PR #17  
**Initial passing PR CI:** `33705460686` — success  
**Latest-head PR CI:** `33705521597` — success  
**Integrated main commit:** `9da8188f8e8586a072f9d02d7d3a902b9b16954d`  
**Merged-main CI:** `33705562544` — success

Phase 6B added:

- canonical `research/planning_tasks/<ptask-id>.json` persistence;
- deterministic atomic save/load/list APIs;
- malformed-record-tolerant filename/ID and duplicate-ID audit;
- typed PlanningReference resolution across canonical Phase 1–5 registries;
- missing dependency and transitive dependency-cycle detection;
- human governing Decision existence, subject/backlink, and outcome checks;
- completion-reference resolution for completed tasks;
- read-only audit behavior with no scheduling or execution;
- package exports, focused regression tests, architecture layout update, and `docs/PLANNING_TASK_REGISTRY.md`.

PlanningTask persistence and audit remain operational only. A clean audit or completed PlanningTask does not approve a Claim, accept a Hypothesis, interpret Evidence, establish experimental validity/reproducibility, approve manuscript content, choose a venue, or authorize submission.

### Phase 6B exit conditions

- [x] canonical PlanningTask repository location exists;
- [x] deterministic save/load/list APIs exist;
- [x] malformed PlanningTask records do not abort audit;
- [x] filename/ID and duplicate-ID integrity checks exist;
- [x] every Phase 6A PlanningReference type resolves against canonical Phase 1–5 state;
- [x] missing dependencies and transitive dependency cycles are audited;
- [x] human governing Decisions are resolved and checked for subject/backlink consistency;
- [x] Decision outcomes are checked against PlanningTask authorization lifecycle;
- [x] completion references are resolved;
- [x] audit is read-only and does not schedule or execute work;
- [x] architecture and registry documentation are updated;
- [x] initial passing PR CI passes (`33705460686`);
- [x] latest-head PR CI passes (`33705521597`);
- [x] PR #17 squash merged (`9da8188f8e8586a072f9d02d7d3a902b9b16954d`);
- [x] merged `main` CI passes (`33705562544`).

## Next bounded increment — Phase 6C: bounded research-planning proposal construction

**Status:** READY after Phase 6B integration.

### Objective

Construct deterministic or explicitly attributed candidate `PlanningTask` proposals from audited repository state without scheduling or executing them. The planner should surface concrete research gaps and bounded next-work candidates while preserving human authority over scientific direction.

### Initial boundary

Phase 6C should at minimum:

- consume only repository state that passes the relevant registry/audit boundary;
- define a framework-neutral proposal input/output contract rather than an agent-framework runtime;
- construct bounded PlanningTask proposals with explicit objective, completion criteria, rationale, priority, typed references, and dependencies;
- identify proposal reasons such as unsupported/weak Claims, missing Evidence, unresolved literature gaps, incomplete experiment provenance, or reproducibility gaps using existing canonical state rather than invented facts;
- keep proposal generation distinct from PlanningTask persistence/acceptance and from execution;
- preserve human authorization requirements for any human-gated task, especially experiment execution;
- provide deterministic tests/fixtures for rule-based proposal construction before adding probabilistic model adapters.

### Non-goals

Do not introduce in Phase 6C:

- autonomous scheduling or workers;
- automatic persistence of proposed tasks as accepted work;
- experiment execution;
- automatic scientific approval or novelty assertions;
- provider-specific agent orchestration;
- manuscript generation;
- submission automation.
