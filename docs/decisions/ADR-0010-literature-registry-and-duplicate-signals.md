# ADR-0010: Literature registry and duplicate-work signals

- **Status:** Accepted
- **Date:** 2026-09-02
- **Phase:** 4B

## Context

Phase 4A established repository-independent contracts for `Citation` and `LiteratureNote`. Phase 4B needs durable repository locations and cross-record auditing.

Bibliographic metadata introduces a specific ambiguity: two repository Citation records may share a DOI, arXiv ID, title, or publication year because they are accidental duplicates, different versions of the same work, metadata errors, or intentionally separate records retained for provenance.

Automatically collapsing such records would convert a heuristic into canonical scholarly identity.

## Decision

### Repository JSON remains canonical

Persist:

```text
literature/metadata/<citation-id>.json
literature/notes/<literature-note-id>.json
```

A database, search index, bibliography file, or external literature service may later derive representations from these records but is not the canonical copy.

### Cross-record audit is read-only

`LiteratureRegistry.audit()` resolves Artifact and Citation references and reports integrity findings. It never rewrites records as part of auditing.

### Preferred-key collisions are errors

`Citation.preferred_key` is repository-facing and must be unambiguous for future bibliography/manuscript tooling. Multiple Citations using the same case-insensitive preferred key are structural errors.

### External-identifier collisions are warnings

A DOI, arXiv ID, PMID, ISBN, or other external identifier appearing on multiple Citation records is a duplicate-work signal. It is reported as a warning and does not merge or delete either record.

### Title/year duplicate signals are warnings

Citations sharing a whitespace-normalized, case-folded title and issued year are reported as possible duplicates. This is intentionally heuristic and therefore cannot mutate canonical identity.

### LiteratureNote provenance must be a subset of Citation provenance

Each note-item Artifact must exist and must belong to the referenced Citation's `source_artifact_ids`. This prevents notes from silently attributing another document's content to the cited work.

## Consequences

- literature state remains Git-reviewable and auditable;
- downstream bibliography tooling can rely on unique preferred keys once errors are resolved;
- preprint/published-version ambiguity remains visible rather than automatically collapsed;
- duplicate detection can become richer later without changing canonical identity rules;
- human or explicitly governed workflows remain responsible for version selection and record merges.

## Rejected alternatives

### Use DOI as canonical ID

Rejected because not all works have DOIs, identifiers can change, and version relationships are not equivalent to repository identity.

### Automatically merge matching DOI/title records

Rejected because identifier collisions and version equivalence require bibliographic judgment and provenance-aware review.

### Allow note provenance from arbitrary repository Artifacts

Rejected because it would make source attribution ambiguous and permit a LiteratureNote attached to one Citation to silently depend on another work.
