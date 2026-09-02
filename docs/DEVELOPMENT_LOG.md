# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-02

**Active phase:** Phase 4C — reviewed literature-to-Evidence proposal bridge  
**Status:** IMPLEMENTED — PR #12 initial CI passed; latest-head/integration gates pending  
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
| Phase 4C — reviewed literature-to-Evidence bridge | INTEGRATION PENDING | PR #12 |

## Phase 4C — reviewed literature-to-Evidence proposal bridge

**Branch:** `phase/4c-literature-evidence-bridge`  
**Integration carrier:** PR #12  
**Initial PR CI:** run `33638611346` — success

### Objective

Provide a deterministic, reviewable bridge from eligible LiteratureNote `source_report` items to canonical `Evidence(kind=literature_statement)` without treating analyst interpretation as source fact or automatically creating scientific support/contradiction relationships.

### Implemented

- added `LiteratureEvidenceBridge` in `src/article_maker/literature_evidence.py`;
- added explicit `LiteratureEvidenceSelection`, `PlannedLiteratureEvidence`, `LiteratureEvidencePlan`, and execution-result objects;
- accepts only `LiteratureStatementType.SOURCE_REPORT` items;
- rejects `analyst_interpretation` items as direct literature Evidence inputs;
- creates deterministic dry-run Evidence previews with stable `ev-lit-*` IDs;
- copies source-report text exactly into Evidence description;
- copies Artifact IDs and locators exactly into Evidence sources;
- preserves Citation ID, LiteratureNote ID, item index/kind/type, and item digest in `metadata.literature_bridge`;
- verifies every source Artifact exists and belongs to the referenced Citation provenance set;
- planning performs no canonical Evidence write;
- hashes the complete plan with `literature_evidence_plan_digest()`;
- execution requires the exact reviewed plan digest;
- execution deep-snapshots the plan before validation;
- stores Citation and LiteratureNote digests in the plan and rejects stale source records before persistence;
- regenerates the expected Evidence from current source records and requires exact equality with the reviewed preview, preventing preview-text/provenance/metadata tampering;
- rejects already-existing Evidence identities rather than overwriting canonical state;
- persists exact reviewed previews through `ClaimEvidenceRegistry`;
- reloads written Evidence and requires exact equality;
- treats graph-audit errors for newly written Evidence as rollback conditions while allowing warning-only `orphan-evidence` state because Phase 4C deliberately creates no ClaimEvidenceLink;
- provides best-effort in-process rollback for files newly created during a failed multi-entry execution;
- exported the bridge API from `article_maker`;
- documented behavior in `docs/LITERATURE_EVIDENCE_BRIDGE.md`;
- recorded durable design choices in `docs/decisions/ADR-0011-reviewed-literature-evidence-promotion.md`;
- added filesystem-backed tests for deterministic/no-write planning, source provenance, analyst-interpretation rejection, invalid selections, reviewed-digest enforcement, stale Note rejection, preview-tamper rejection, successful exact persistence, and existing-Evidence conflict protection.

### Scientific authority boundary

Phase 4C creates provenance-bearing Evidence only. It does not decide what that Evidence means for any Claim.

The bridge must not:

- create or accept ClaimEvidenceLink records;
- decide `supports` or `contradicts` relationships;
- approve/reject/supersede Claims;
- promote analyst interpretations as source-reported Evidence;
- assert novelty;
- merge Citations;
- fetch, parse, summarize, or embed literature;
- invoke an LLM.

### Validation and scope audit

- `main..phase/4c-literature-evidence-bridge` is ahead-only and limited to bridge runtime, exports, tests, documentation/ADR, and this handoff state;
- initial PR #12 CI run `33638611346` completed successfully, including all existing Phase 1–4B tests and the new Phase 4C suite;
- no live literature retrieval, semantic parser, LLM extraction/summarization, embeddings/RAG, automatic ClaimEvidenceLink creation/acceptance, novelty judgment, manuscript generation, or venue formatting was introduced.

### Phase 4C exit conditions

- [x] source-report-only eligibility is enforced;
- [x] deterministic dry-run Evidence projection exists;
- [x] exact Artifact + locator provenance is preserved;
- [x] Citation/LiteratureNote traceability metadata is preserved;
- [x] planning writes no Evidence;
- [x] reviewed digest is required for execution;
- [x] stale Citation/LiteratureNote records are rejected;
- [x] reviewed preview must be reproducible exactly from source records;
- [x] existing Evidence identities cannot be overwritten;
- [x] canonical Evidence is persisted only by explicit execution;
- [x] post-write equality/audit checks exist;
- [x] material choices are recorded in ADR-0011;
- [x] bounded-scope audit passes;
- [x] initial PR CI passes;
- [ ] latest-head PR CI passes after this handoff update;
- [ ] PR #12 merged and `main` push CI passes.

## Next bounded increment — Phase 5A: typed Experiment provenance contracts

**Status:** BLOCKED until Phase 4C integration is complete.

### Objective

Define the framework-neutral canonical contracts for reproducible Experiment identity, inputs/configuration, code/environment provenance, execution status, outputs, and run relationships without implementing a scheduler, remote runner, or scientific interpretation layer.

### Required boundary

At minimum Phase 5A should define:

- stable Experiment and ExperimentRun identities;
- explicit input Artifact/config references;
- code revision and execution-environment provenance;
- deterministic parameter/config representation;
- run lifecycle/status separated from scientific result quality;
- output Artifact references;
- rerun/reproduction lineage;
- failure/partial-run representation;
- framework-neutral JSON Schema plus Python validation;
- representative positive/negative contract tests;
- an ADR for identity/provenance choices that constrain later execution.

### Non-goals

Do not introduce in Phase 5A:

- job scheduling or remote execution;
- container orchestration;
- cloud/HPC runners;
- automated statistical interpretation;
- automatic Evidence or Claim creation from experiment outputs;
- LLM/agent runtime orchestration;
- manuscript generation.
