# Literature and Citation Contracts

Phase 4A defines the canonical object-level contracts for bibliographic identity and structured literature notes. It does not retrieve, parse, summarize, rank, or judge papers.

## Canonical objects

### Citation

`Citation` (`cit-*`) records bibliographic identity and repository provenance for one literature work.

Required facts are intentionally small:

- stable internal `citation_id`;
- work type;
- title;
- at least one author;
- at least one registered Artifact reference that is the repository provenance for the work.

Optional bibliographic fields include issued date, container title, publisher, volume, issue, pages, a preferred citation key, and external identifiers such as DOI/arXiv/PMID/ISBN.

The internal `citation_id` is authoritative inside `article_maker`. External identifiers are metadata and must not be treated as the only durable identity because they may be absent, corrected, aliased, or represented differently across sources.

Phase 4A validates only Artifact ID grammar. Repository-level existence, Artifact kind, citation-key uniqueness, external-identifier collisions, and note-to-citation provenance consistency are deferred to the repository registry phase.

### LiteratureNote

`LiteratureNote` (`litn-*`) records structured human or agent reading notes attached to exactly one Citation.

A note contains one or more `LiteratureNoteItem` records. Each item has:

- a semantic kind such as `method`, `reported_finding`, `limitation`, `relevance`, or `comparison`;
- a `statement_type`;
- nonblank text;
- at least one precise Artifact + locator reference.

The two statement types are deliberately explicit:

- `source_report`: what the literature source reports or states;
- `analyst_interpretation`: how a human or agent interprets, compares, or contextualizes the source.

Both require source references. This does not mean both have equal scientific authority; it means both remain auditable back to the material being read.

## Literature notes are not Evidence by default

A `LiteratureNoteItem` is a reading record, not automatically a canonical `Evidence` object and not automatically an accepted Claim-Evidence relation.

A later bounded workflow may propose promotion of a traceable `source_report` into literature-derived Evidence, but Phase 4A does not perform that transition. Any materially interpretive Claim-Evidence relation remains subject to the existing human governance boundary.

## Novelty boundary

The Phase 4A structured vocabulary intentionally contains no `novelty_assertion`, novelty score, priority claim, or automatic state transition.

Literature notes may record comparisons and relevance, but a statement that the current research is novel remains a higher-level research judgment and human authority concern.

## Provenance boundary

Every Citation must point to at least one canonical Artifact. Every LiteratureNote item must point to one or more Artifact locations.

Object-level validation cannot prove that:

- the Artifact exists;
- the Artifact belongs to the Citation;
- the locator exists inside the file;
- the bibliographic metadata exactly matches the source;
- two Citation records represent the same real-world work.

Those repository-level checks belong to Phase 4B.

## Framework-neutral contract

The cross-language contract is `schemas/literature.schema.json` using JSON Schema Draft 2020-12. The Pydantic models in `src/article_maker/literature.py` are the Python validation implementation, not a replacement for the external contract.

## Explicit Phase 4A non-goals

Phase 4A introduces no:

- live Crossref, Semantic Scholar, PubMed, arXiv, or other network client;
- automatic PDF/PPT parsing;
- LLM extraction or summarization;
- embeddings or vector retrieval;
- citation recommendation;
- automatic novelty judgment;
- manuscript bibliography generation;
- venue-specific citation formatting.
