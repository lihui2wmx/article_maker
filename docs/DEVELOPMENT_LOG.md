# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-02

**Active phase:** Phase 4A — typed literature and citation contracts  
**Status:** IMPLEMENTED — PR #10 initial CI passed; latest-head/integration gates pending  
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
| Phase 4A — Literature/Citation contracts | INTEGRATION PENDING | PR #10 |

## Phase 4A — typed literature and citation contracts

**Branch:** `phase/4a-literature-citation-contracts`  
**Integration carrier:** PR #10  
**Initial PR CI:** run `33636442838` — success

### Objective

Define framework-neutral canonical bibliographic and structured literature-reading contracts while separating source metadata, source-reported statements, analyst interpretation, scientific Evidence, and novelty judgments.

### Implemented

- added stable `cit-*` Citation IDs and `litn-*` LiteratureNote IDs;
- added `Citation` as canonical bibliographic identity plus repository Artifact provenance;
- kept DOI/arXiv/PMID/ISBN identifiers as external metadata rather than internal primary keys;
- added work type, title, structured author records, optional ORCID, partial ISO issued dates, container/publisher/volume/issue/pages fields, optional preferred citation key, external identifiers, and JSON metadata;
- required every Citation to reference at least one canonical Artifact ID;
- added `LiteratureNote` as a structured human/agent reading record attached to one Citation;
- added traceable note items with semantic kinds such as method, reported finding, limitation, relevance, and comparison;
- explicitly distinguished `source_report` from `analyst_interpretation`;
- required every note item to reference at least one Artifact + nonblank locator;
- explicitly kept LiteratureNote items separate from canonical `Evidence`, Claim-Evidence links, Claims, and novelty assertions;
- deliberately omitted novelty scores and novelty-assertion note kinds;
- added Draft 2020-12 `schemas/literature.schema.json`;
- added Python/Pydantic implementation in `src/article_maker/literature.py`;
- exported literature contracts and shared ID validators;
- documented the contract in `docs/LITERATURE_CONTRACTS.md`;
- recorded durable identity/interpretation choices in `docs/decisions/ADR-0009-literature-identity-and-interpretation-separation.md`;
- added positive/negative Python and JSON Schema tests for identity, provenance, authors, dates, duplicate identifiers, source locators, statement-type separation, duplicate notes/tags, JSON metadata, and the novelty boundary.

### Authority and interpretation boundary

Phase 4A permits agents to record traceable literature notes, including analyst interpretations. Such notes are not automatically scientific Evidence and do not automatically establish support, contradiction, or novelty.

A later bounded workflow may propose conversion of literature `source_report` records into literature-derived Evidence, but existing human-governed scientific transitions remain authoritative.

### Validation and scope audit

- `main..phase/4a-literature-citation-contracts` is ahead-only and limited to literature contracts, schema, IDs, exports, tests, docs/ADR, and canonical handoff state;
- initial PR #10 CI run `33636442838` completed successfully;
- no live literature search/download client, PDF/PPT parsing, LLM extraction/summarization, embeddings/RAG, citation recommendation, novelty judgment, manuscript bibliography generation, or venue formatting was introduced.

### Phase 4A exit conditions

- [x] framework-neutral Citation contract exists;
- [x] framework-neutral LiteratureNote contract exists;
- [x] internal Citation identity is independent from external identifier namespaces;
- [x] Citation repository provenance is explicit;
- [x] source-reported literature content is distinct from analyst interpretation;
- [x] every structured note item has precise repository provenance;
- [x] literature notes do not automatically become Evidence or novelty claims;
- [x] Python and JSON Schema positive/negative tests exist;
- [x] material choices are recorded in ADR-0009;
- [x] bounded-scope audit passes;
- [x] initial PR CI passes;
- [ ] latest-head PR CI passes after this handoff update;
- [ ] PR #10 merged and `main` push CI passes.

## Next bounded increment — Phase 4B: repository literature registry and citation-integrity audit

**Status:** BLOCKED until Phase 4A integration is complete.

### Objective

Persist Citation and LiteratureNote records in deterministic repository locations and audit cross-record provenance/identity integrity without automatically merging works, promoting notes to Evidence, retrieving papers, or judging novelty.

### Expected canonical locations

```text
literature/metadata/<citation-id>.json
literature/notes/<literature-note-id>.json
```

### Required audit boundary

At minimum Phase 4B should check:

- Citation -> Artifact existence;
- LiteratureNote -> Citation existence;
- LiteratureNote source Artifact existence;
- LiteratureNote source Artifact belongs to the referenced Citation provenance set;
- duplicate preferred citation keys;
- repeated external identifier values across distinct Citations;
- filename/ID mismatch and duplicate IDs;
- malformed-record tolerance;
- duplicate-work signals are warnings/review tasks, not automatic record merges.

### Non-goals

Do not introduce in Phase 4B:

- live literature search/download clients;
- PDF/PPT semantic parsing;
- LLM summarization/extraction;
- embeddings/vector retrieval;
- automatic note-to-Evidence promotion;
- automatic novelty assertions;
- manuscript generation or venue-specific formatting.
