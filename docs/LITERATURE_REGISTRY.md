# Literature Registry and Citation-Integrity Audit

Phase 4B persists the Phase 4A literature contracts as repository state and audits cross-record integrity without making scientific or bibliographic merge decisions automatically.

## Canonical locations

```text
literature/
├── metadata/
│   └── <citation-id>.json
└── notes/
    └── <literature-note-id>.json
```

Each file stores exactly one validated Phase 4A object. JSON is UTF-8, deterministically serialized, and replaced atomically per record.

## Registry API

`LiteratureRegistry` provides typed operations:

- `save_citation()` / `load_citation()` / `list_citations()`;
- `save_note()` / `load_note()` / `list_notes()`;
- `audit()` for malformed-record-tolerant cross-record integrity checks.

Save operations persist already validated objects. They deliberately do not infer work identity, merge records, retrieve papers, promote notes to Evidence, or mutate scientific state.

## Audit errors

Errors indicate repository structure or reference integrity that must be repaired before downstream automation should rely on the literature state.

Current error classes include:

- malformed Citation or LiteratureNote records;
- filename/ID mismatch;
- duplicate internal IDs materialized by inconsistent files;
- missing Citation source Artifact;
- LiteratureNote referencing a missing Citation;
- LiteratureNote source Artifact missing from the Artifact registry;
- LiteratureNote source Artifact outside the referenced Citation's provenance set;
- duplicate `preferred_key` values across Citations.

`preferred_key` collisions are errors because later bibliography and manuscript tooling needs an unambiguous repository-local key mapping.

## Audit warnings

Warnings surface review tasks without mutating or deduplicating canonical records.

Current warning classes include:

- the same external identifier value, such as DOI or arXiv ID, on multiple Citation records;
- multiple Citations with the same normalized title and issued year.

These are signals of possible duplicate versions or metadata collisions, not proof that two Citation records represent the same scholarly work. Both records remain canonical until an explicit later workflow or human decision resolves them.

## Provenance rule

Every Citation points to one or more registered Artifacts. Every LiteratureNote item points to an Artifact and locator. Phase 4B additionally requires each note-item Artifact to belong to the provenance set of the referenced Citation.

This means a note about Citation A cannot silently quote or interpret Artifact B even if Artifact B exists elsewhere in the repository.

## Authority boundary

The literature audit is read-only. It must not:

- merge Citation records;
- select a preferred publication version;
- rewrite DOI/arXiv metadata;
- promote a LiteratureNote item to Evidence;
- create ClaimEvidenceLink records;
- assert novelty;
- decide that one paper supersedes another;
- fetch or parse external literature.

Such actions belong to later bounded workflows with explicit review semantics.
