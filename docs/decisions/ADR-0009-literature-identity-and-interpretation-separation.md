# ADR-0009: Separate Bibliographic Identity from Literature Interpretation

## Status

Accepted for Phase 4A.

## Context

The literature layer must later support citation integrity, prior-work comparison, retrieval, evidence extraction, and novelty review. A single monolithic "paper summary" object would collapse several materially different concerns:

1. bibliographic identity and metadata;
2. repository provenance for the actual source material;
3. what the source reports;
4. how a human or agent interprets the source;
5. whether a statement should become canonical scientific Evidence;
6. whether the current work is novel relative to prior art.

Collapsing these concerns would make provenance weak and would allow probabilistic summaries to masquerade as bibliographic or scientific truth.

## Decision

Phase 4A defines two canonical object types.

### Citation

`Citation` uses an internal stable `cit-*` identifier. DOI, arXiv, PMID, ISBN, and similar identifiers are external metadata rather than internal primary keys.

A Citation must reference at least one repository Artifact as provenance. Bibliographic fields are deliberately minimal and framework-neutral.

### LiteratureNote

`LiteratureNote` uses an internal stable `litn-*` identifier and points to exactly one Citation.

Each note item explicitly distinguishes:

- `source_report`: a statement attributed to the literature source;
- `analyst_interpretation`: a human/agent interpretation, comparison, or relevance judgment.

Every note item requires one or more Artifact + locator references.

LiteratureNote items do not automatically become `Evidence`, Claim-Evidence links, Claims, or novelty assertions.

### Novelty

No automatic novelty field, score, or authority transition is defined in Phase 4A. Comparison notes are allowed as traceable analysis, but novelty remains a later research judgment subject to human authority.

## Consequences

### Positive

- bibliographic metadata remains distinguishable from AI-generated interpretation;
- a missing or corrected DOI does not change internal Citation identity;
- literature notes are traceable to precise repository locations;
- later extraction workflows can distinguish source-reported content from analyst inference;
- promotion from literature reading notes to scientific Evidence can be explicit and auditable;
- novelty analysis can consume structured literature state without automatically asserting novelty.

### Costs

- repository-level duplicate-work resolution is not solved at object-contract level;
- preferred citation-key uniqueness requires a registry-level audit;
- external identifier normalization/collision policy remains to be defined;
- locators are syntactically nonblank but cannot yet be verified against file contents;
- the same paper may temporarily have multiple Citation records until Phase 4B detects or resolves ambiguity.

## Rejected alternatives

### Use DOI as the canonical Citation ID

Rejected because many works lack DOI identifiers, identifiers may be corrected or duplicated across representations, and repository identity should not depend on an external provider namespace.

### Store one free-form paper summary

Rejected because it obscures the distinction between source statements and analyst interpretation and provides poor machine-auditable provenance.

### Convert every reported literature statement directly into Evidence

Rejected because a reading note is not automatically a vetted scientific Evidence record. Promotion should be an explicit later workflow.

### Add an automatic novelty score

Rejected because novelty is a high-impact research judgment and cannot be reduced to an ungoverned model-generated scalar in this phase.

## Follow-up

Phase 4B should add deterministic repository persistence and audit for Citation/LiteratureNote records, including Artifact existence/type checks, note-to-citation provenance consistency, duplicate preferred keys, external identifier collisions, orphan notes, and duplicate-work warnings without automatically merging records.
