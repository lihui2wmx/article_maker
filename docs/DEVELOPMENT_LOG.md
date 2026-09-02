# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-02

**Active next phase:** Phase 5A — typed Experiment provenance contracts  
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

## Phase 4C closure

**Branch:** `phase/4c-literature-evidence-bridge`  
**Integration carrier:** PR #12  
**Initial PR CI:** `33638611346` — success  
**Latest-head PR CI:** `33638732212` — success  
**Integrated main commit:** `ffe4c5d8764f3504abf9af47927470a44bc7e2ef`  
**Merged-main CI:** `33638830523` — success

Phase 4C added a deterministic reviewed bridge from LiteratureNote `source_report` items to `Evidence(kind=literature_statement)` with:

- exact source text and Artifact+locator provenance preservation;
- deterministic `ev-lit-*` identity and complete dry-run previews;
- Citation/LiteratureNote/item traceability metadata;
- `analyst_interpretation` rejection as direct literature Evidence;
- exact reviewed-plan digest binding;
- stale Citation/LiteratureNote rejection;
- deterministic preview regeneration to reject tampering;
- explicit execution only, with no Evidence write during planning;
- existing-Evidence conflict rejection;
- post-write equality and graph-audit checks;
- best-effort in-process rollback for newly written files.

Scientific interpretation remains separate: Phase 4C does not create or accept ClaimEvidenceLink records, decide support/contradiction, approve Claims, assert novelty, retrieve/parse literature, or invoke an LLM.

Documentation:

- `docs/LITERATURE_EVIDENCE_BRIDGE.md`
- `docs/decisions/ADR-0011-reviewed-literature-evidence-promotion.md`

## Next bounded increment — Phase 5A: typed Experiment provenance contracts

**Status:** READY.

### Objective

Define framework-neutral canonical contracts for reproducible Experiment identity, intended configuration, individual run provenance, execution status, inputs, outputs, and rerun/reproduction relationships without implementing a scheduler or interpreting experimental results scientifically.

### Required outputs

At minimum define:

- stable `Experiment` and `ExperimentRun` identities;
- explicit input Artifact/config references;
- deterministic parameter/config representation;
- code revision and execution-environment provenance;
- run lifecycle/status separated from scientific result quality;
- output Artifact references;
- rerun/reproduction lineage;
- failure and partial-run representation;
- framework-neutral JSON Schema plus Python validation;
- representative valid/invalid tests;
- an ADR for identity/provenance choices that constrain later execution.

### Non-goals

Do not introduce in Phase 5A:

- job scheduling or remote execution;
- container orchestration;
- cloud/HPC runners;
- automatic statistical/scientific interpretation;
- automatic Evidence or Claim creation from experiment outputs;
- LLM/agent runtime orchestration;
- manuscript generation.
