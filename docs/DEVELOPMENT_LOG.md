# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-02

**Active phase:** Phase 3B — repository Claim/Evidence registry and graph audit  
**Status:** IMPLEMENTED — PR #9 initial CI passed; latest-head/integration gates pending  
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
| Phase 3B — repository Claim/Evidence registry/audit | INTEGRATION PENDING | PR #9 |

## Phase 3B — repository Claim/Evidence registry and graph audit

**Branch:** `phase/3b-claim-evidence-registry`  
**Integration carrier:** PR #9  
**Initial PR CI:** run `33634840309` — success

### Objective

Persist `Claim`, `Evidence`, and `ClaimEvidenceLink` records in deterministic repository locations and audit repository-level scientific graph integrity while preserving the Phase 3A human-authority boundary.

### Implemented

- added `ClaimEvidenceRegistry` in `src/article_maker/claim_registry.py`;
- added canonical locations:
  - `claims/<claim-id>.json`;
  - `evidence/<evidence-id>.json`;
  - `evidence/links/<link-id>.json`;
- added typed save/load/list APIs for all three Phase 3 objects;
- added deterministic UTF-8 JSON serialization with per-record atomic replacement;
- added malformed-record-tolerant read-only graph audit;
- resolved Claim -> ResearchQuestion references;
- resolved optional Claim -> Hypothesis references and verified the Hypothesis belongs to the same ResearchQuestion;
- resolved Claim -> dependent Claim references;
- added repository-level Claim dependency cycle detection;
- resolved Evidence -> Artifact provenance sources through the Phase 1 ArtifactRegistry;
- resolved ClaimEvidenceLink -> Claim and Evidence endpoints;
- resolved Claim/Link -> governing Decision references through `research/decisions/`;
- verified governing Decision subject backlinks and Decision outcome -> lifecycle consistency;
- audited Claim/Link Decision histories for missing predecessors, cross-subject predecessors, timestamp ordering, branches, cycles, ambiguous roots/heads, and stale governing references;
- preserved simultaneous accepted `supports` and `contradicts` relations instead of suppressing either side;
- added explicit graph audit severities:
  - `error` for structural/governance integrity failures;
  - `warning` for scientific gaps/conflicts that must not automatically override human decisions;
- added warning `approved-claim-without-accepted-support`;
- added warning `accepted-evidence-conflict`;
- added warning `orphan-evidence`;
- documented registry/audit semantics in `docs/CLAIM_EVIDENCE_REGISTRY.md`;
- recorded durable design choices in `docs/decisions/ADR-0008-repository-claim-evidence-graph-audit.md`;
- exported the registry API from `article_maker`;
- added filesystem-backed tests for coherent graphs, persistence, missing cross-domain references, Hypothesis/Question mismatch, dependency cycles, scientific warnings, Decision outcome/history integrity, malformed-record tolerance, unsafe registry paths, and missing loads.

### Scientific authority boundary

The graph audit may report that an approved Claim lacks accepted support or has accepted contradictory Evidence. Those conditions are warnings, not automatic lifecycle mutations.

The audit must not:

- revoke or grant Claim approval;
- accept or reject a ClaimEvidenceLink;
- suppress inconvenient Evidence;
- decide which side of conflicting Evidence is scientifically stronger;
- infer novelty or manuscript suitability.

Human `Decision` records remain authoritative for scientific transitions.

### Validation and scope audit

- `main..phase/3b-claim-evidence-registry` is ahead-only and limited to registry runtime, exports, tests, documentation/ADR, and this handoff state;
- initial PR #9 CI run `33634840309` completed successfully, including all existing Phase 1/2/3A tests and the new Phase 3B graph suite;
- no semantic extraction, LLM provider, agent runtime, RAG/vector indexing, graph database as canonical state, confidence scoring, novelty judgment, manuscript generation, or experiment orchestration was introduced.

### Phase 3B exit conditions

- [x] deterministic Claim/Evidence/Link canonical locations exist;
- [x] typed save/load/list APIs exist;
- [x] malformed-record-tolerant read-only graph audit exists;
- [x] Claim -> ResearchQuestion/Hypothesis consistency is audited;
- [x] Claim dependency existence and cycles are audited;
- [x] Evidence -> Artifact provenance resolution is audited;
- [x] ClaimEvidenceLink endpoints are audited;
- [x] Claim/Link Decision governance and history are audited;
- [x] structural errors are distinct from scientific warnings;
- [x] accepted supporting and contradicting Evidence remain simultaneously visible;
- [x] approved Claims expose missing accepted support without automatic state mutation;
- [x] material choices are recorded in ADR-0008;
- [x] bounded-scope audit passes;
- [x] initial PR CI passes;
- [ ] latest-head PR CI passes after this canonical handoff update;
- [ ] PR #9 merged and `main` push CI passes.

## Next bounded increment — Phase 4A: typed literature and citation contracts

**Status:** BLOCKED until Phase 3B integration is complete.

### Objective

Define framework-neutral canonical contracts for bibliographic `Citation` / literature-source metadata and structured paper notes that can later support literature extraction, citation integrity, prior-work comparison, and novelty analysis without yet introducing network search, semantic retrieval, LLM extraction, or automatic novelty assertions.

### Expected boundary

The Phase 4A contract should distinguish bibliographic identity/metadata from AI or human interpretation, preserve provenance back to registered literature Artifacts, and keep novelty claims outside automated authority.

### Non-goals

Do not introduce in Phase 4A:

- live literature search/download clients;
- LLM-based PDF parsing or summarization;
- embeddings/vector search;
- automatic novelty judgment;
- manuscript generation;
- venue-specific writing behavior.
