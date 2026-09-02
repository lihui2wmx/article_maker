# Development Log

This is the canonical implementation handoff for `article_maker`.

New agents should read, in order:

1. `PROJECT.md`
2. `AGENTS.md`
3. `docs/ARCHITECTURE.md`
4. this file

Detailed historical phase notes remain available in Git history. This compact form is authoritative for the current implementation state and next bounded task.

## Current repository state — 2026-09-02

**Active phase:** Phase 4B — repository literature registry and citation-integrity audit  
**Status:** IMPLEMENTED — PR #11 initial CI passed; latest-head/integration gates pending  
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
| Phase 4B — literature registry/citation-integrity audit | INTEGRATION PENDING | PR #11 |

## Phase 4B — repository literature registry and citation-integrity audit

**Branch:** `phase/4b-literature-registry`  
**Integration carrier:** PR #11  
**Initial PR CI:** run `33637342522` — success

### Objective

Persist `Citation` and `LiteratureNote` records in deterministic repository locations and audit bibliographic/provenance integrity without automatically merging works, selecting publication versions, promoting notes to Evidence, retrieving papers, or judging novelty.

### Implemented

- added `LiteratureRegistry` in `src/article_maker/literature_registry.py`;
- added canonical locations:
  - `literature/metadata/<citation-id>.json`;
  - `literature/notes/<literature-note-id>.json`;
- added typed save/load/list APIs for Citation and LiteratureNote records;
- added deterministic UTF-8 JSON serialization with per-record atomic replacement;
- added malformed-record-tolerant read-only audit;
- resolved Citation -> Artifact provenance references through the Phase 1 ArtifactRegistry;
- resolved LiteratureNote -> Citation references;
- resolved every note-item source Artifact;
- required note-item source Artifacts to belong to the referenced Citation provenance set;
- audited filename/ID mismatches and duplicate internal IDs;
- classified duplicate case-insensitive `preferred_key` values as structural errors;
- classified repeated external identifiers across Citations as warnings/review signals only;
- classified same normalized title + issued-year groups as possible-duplicate-work warnings only;
- deliberately retained all Citation records when duplicate-work warnings are present;
- documented registry/audit semantics in `docs/LITERATURE_REGISTRY.md`;
- recorded durable duplicate-signal choices in `docs/decisions/ADR-0010-literature-registry-and-duplicate-signals.md`;
- exported the literature registry API from `article_maker`;
- added filesystem-backed tests for clean persistence/audit, missing Artifact/Citation references, provenance-subset enforcement, preferred-key collisions, external-identifier warnings, title/year duplicate warnings, malformed-record tolerance, filename/ID mismatch, duplicate IDs, unsafe registry paths, and missing loads.

### Authority boundary

Phase 4B audit is read-only. Duplicate-work signals do not prove bibliographic equivalence and therefore cannot mutate canonical Citation identity.

The audit must not:

- merge or delete Citation records;
- select a preferred publication/preprint version;
- rewrite external identifiers;
- promote LiteratureNote items to Evidence;
- create ClaimEvidenceLink records;
- assert novelty;
- fetch or semantically parse literature.

### Validation and scope audit

- `main..phase/4b-literature-registry` is ahead-only and limited to registry runtime, exports, tests, documentation/ADR, and this handoff state;
- initial PR #11 CI run `33637342522` completed successfully, including all existing Phase 1–4A tests and the new Phase 4B suite;
- no live literature search/download client, semantic parser, LLM extraction/summarization, embeddings/RAG, automatic record merge, automatic note-to-Evidence promotion, novelty judgment, manuscript generation, or venue formatting was introduced.

### Phase 4B exit conditions

- [x] deterministic Citation/Note canonical locations exist;
- [x] typed save/load/list APIs exist;
- [x] malformed-record-tolerant read-only audit exists;
- [x] Citation -> Artifact provenance is audited;
- [x] LiteratureNote -> Citation is audited;
- [x] note Artifact existence and Citation-provenance membership are audited;
- [x] preferred-key collisions are structural errors;
- [x] external-identifier and title/year duplicate-work signals are warnings only;
- [x] duplicate signals never auto-merge canonical records;
- [x] filename/ID mismatch and duplicate internal IDs are audited;
- [x] material choices are recorded in ADR-0010;
- [x] bounded-scope audit passes;
- [x] initial PR CI passes;
- [ ] latest-head PR CI passes after this canonical handoff update;
- [ ] PR #11 merged and `main` push CI passes.

## Next bounded increment — Phase 4C: reviewed literature-to-Evidence proposal bridge

**Status:** BLOCKED until Phase 4B integration is complete.

### Objective

Create a deterministic, reviewable bridge that can transform eligible `LiteratureNote` `source_report` items into proposed `Evidence(kind=literature_statement)` objects without writing Evidence automatically or interpreting analyst notes as source facts.

### Required boundary

At minimum Phase 4C should:

- accept only `source_report` note items as eligible source material;
- preserve exact Artifact + locator provenance;
- preserve Citation and LiteratureNote identifiers in proposal metadata;
- produce deterministic dry-run Evidence previews;
- reject analyst interpretations as direct literature Evidence inputs;
- detect stale literature records before execution or persistence;
- require an explicit reviewed execution step before canonical Evidence write.

### Non-goals

Do not introduce in Phase 4C:

- live literature search/download clients;
- PDF/PPT semantic parsing;
- LLM summarization/extraction;
- embeddings/vector retrieval;
- automatic ClaimEvidenceLink creation or acceptance;
- automatic novelty assertions;
- manuscript generation or venue-specific formatting.
