# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in the Git history of this file. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-02

**Active next phase:** Phase 3B — repository Claim/Evidence registry and graph audit  
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

All completed phases above passed their PR CI and post-merge `main` CI gates.

## Phase 3A — typed Claim/Evidence contracts

**Branch:** `phase/3a-claim-evidence-contracts`  
**Integration carrier:** PR #8  
**Integrated main commit:** `e7f6e24fd1a7d4fee1092820c3f5e428fa322e9f`  
**PR latest-head CI:** run `33632725357` — success  
**Merged-main CI:** run `33632985211` — success

**Status:** COMPLETE.

### Implemented

- added stable scientific identifiers:
  - `clm-*` for `Claim`;
  - `ev-*` for `Evidence`;
  - `cel-*` for `ClaimEvidenceLink`;
- added framework-neutral Draft 2020-12 contract in `schemas/claim-evidence.schema.json`;
- added Python/Pydantic implementation in `src/article_maker/claim_evidence.py`;
- added `Claim` lifecycle:
  - `candidate`;
  - `approved`;
  - `rejected`;
  - `superseded`;
- candidate Claims may be proposed by human or agent;
- every non-candidate Claim requires an explicit human `Decision` reference;
- added `Evidence` as a provenance-bearing record with at least one canonical Artifact source and optional locator;
- deliberately gave Evidence no approval lifecycle, separating recorded material from scientific interpretation;
- added `ClaimEvidenceLink` with explicit relation:
  - `supports`;
  - `contradicts`;
- added link lifecycle:
  - `proposed`;
  - `accepted`;
  - `rejected`;
  - `superseded`;
- every non-proposed Claim-Evidence interpretation requires an explicit human `Decision` reference;
- added Claim dependency references with duplicate/self-dependency rejection;
- extended generic `DecisionSubjectType` with `claim` and `claim_evidence_link` while preserving `authority = human`;
- preserved the Phase 2 registry boundary so Phase 3 Decisions are not misclassified as missing Hypothesis/ResearchQuestion subjects;
- added Python and JSON Schema positive/negative contract tests;
- added Phase 2 compatibility coverage;
- documented the scientific-state contract in `docs/CLAIM_EVIDENCE.md`;
- recorded the architecture decision in `docs/decisions/ADR-0007-claim-evidence-separation-and-governance.md`.

### Phase 3A authority boundary

Agents may:

- propose candidate Claims;
- record provenance-bearing Evidence;
- propose that Evidence supports or contradicts a Claim;
- explain the rationale for those proposals.

Agents may not independently make canonical:

- Claim approval/rejection/supersession;
- acceptance/rejection/supersession of materially interpretive Claim-Evidence relations.

Those remain human scientific authority gates represented by `Decision` records.

### Phase 3A exit conditions

- [x] framework-neutral Claim/Evidence/Link schema exists;
- [x] Python validation implementation exists;
- [x] Claim approval remains human-governed;
- [x] Evidence provenance is explicit and separate from interpretation;
- [x] support/contradiction is a first-class governed relation;
- [x] Decision supports Claim/Link subjects without weakening human authority;
- [x] Phase 2 audit remains compatible;
- [x] positive/negative contract tests exist;
- [x] documentation and ADR exist;
- [x] bounded scope preserved;
- [x] PR latest-head CI passes;
- [x] PR #8 merged;
- [x] merged `main` CI passes.

### Non-goals preserved

Phase 3A introduced no:

- semantic Claim/Evidence extraction agent;
- LLM provider or Agent Runtime;
- embeddings, vector database, or RAG;
- graph database as canonical state;
- automated novelty judgment;
- automated scientific approval;
- manuscript generation;
- experiment orchestration.

## Phase 3B — repository Claim/Evidence registry and graph audit

**Status:** READY.

### Objective

Persist `Claim`, `Evidence`, and `ClaimEvidenceLink` records in deterministic repository locations and audit repository-level scientific graph integrity while preserving the Phase 3A human-authority boundary.

### Required outputs

Phase 3B should add deterministic canonical locations, expected to align with the architecture layout:

```text
claims/<claim-id>.json
evidence/<evidence-id>.json
evidence/links/<link-id>.json
```

The implementation should provide typed save/load/list operations and a malformed-record-tolerant read-only graph audit.

### Required graph checks

At minimum audit:

- Claim -> ResearchQuestion existence;
- optional Claim -> Hypothesis existence;
- Claim Hypothesis belongs to the same ResearchQuestion;
- Claim -> Claim dependency existence;
- Claim dependency self-reference/cycles at repository level;
- Evidence -> Artifact source existence;
- ClaimEvidenceLink -> Claim existence;
- ClaimEvidenceLink -> Evidence existence;
- Claim/Link governing Decision existence;
- governing Decision subject backlink;
- Decision outcome -> Claim/Link lifecycle consistency;
- Decision-history integrity for Claim/Link subjects;
- accepted support/contradiction relations remain visible simultaneously rather than suppressing inconvenient evidence;
- approved Claims expose whether accepted supporting evidence exists, without automatically approving/rejecting the Claim.

### Explicit non-goals for Phase 3B

Do not introduce in this increment:

- automatic parsing/extraction from PDF/PPT/literature;
- LLM Provider abstraction;
- Agent Runtime/orchestration;
- semantic retrieval/vector indexing;
- automatic evidence-strength/confidence scoring;
- novelty assertions;
- manuscript generation;
- experiment orchestration;
- graph database as the sole canonical store.

### Next bounded task

Implement and review the **Phase 3B repository Claim/Evidence registry and read-only graph consistency audit**. Keep repository JSON records canonical and keep graph/database/index representations derived.
