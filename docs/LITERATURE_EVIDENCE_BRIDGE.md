# Reviewed Literature-to-Evidence Bridge

Phase 4C connects structured literature reading state to the scientific Evidence layer without turning analyst interpretation into source fact.

## Purpose

The bridge accepts selected `LiteratureNote` items whose `statement_type` is exactly `source_report` and creates deterministic dry-run `Evidence(kind=literature_statement)` previews.

Planning is non-mutating. Canonical Evidence is written only through an explicit reviewed execution call bound to the exact plan digest.

## Flow

```text
Citation + LiteratureNote
        ↓
selected source_report item
        ↓
deterministic Evidence preview
        ↓
review plan digest
        ↓
reload Citation + LiteratureNote
        ↓
stale-source and reproducibility checks
        ↓
explicit execute
        ↓
evidence/<evidence-id>.json
```

## Deterministic projection

For each eligible note item, the preview:

- uses `EvidenceKind.LITERATURE_STATEMENT`;
- copies the source-report text exactly into `Evidence.description`;
- copies each Artifact ID and locator exactly into `Evidence.sources`;
- preserves the note's `recorded_by` attribution;
- records Citation ID, LiteratureNote ID, item index, note kind, statement type, and an item digest in `metadata.literature_bridge`;
- derives a stable `ev-lit-*` ID from Citation identity, LiteratureNote identity, and the canonical note-item content.

The planner does not write Evidence.

## Eligibility

Only `LiteratureStatementType.SOURCE_REPORT` is eligible.

`analyst_interpretation` is deliberately rejected as a direct Evidence input. An analyst statement may later motivate a Claim or review task, but it cannot be represented as though it were reported by the cited source.

All source Artifacts must:

1. exist in the Artifact registry; and
2. belong to the referenced Citation's `source_artifact_ids` provenance set.

## Review binding

`literature_evidence_plan_digest()` hashes the complete ordered plan, including:

- source Citation and LiteratureNote IDs;
- source-record digests;
- selected item indices;
- exact Evidence previews.

`execute()` requires that exact digest as `reviewed_digest`.

A different digest is rejected before any write.

## Stale-source protection

Before persistence, execution reloads the Citation and LiteratureNote and compares them with the digests captured at planning time.

If either record changed after review, execution fails with `LiteratureEvidenceStaleError` and performs no write.

The executor then regenerates the expected Evidence from the current source-report item and requires it to match the reviewed preview exactly. This prevents a modified description, source locator, or metadata payload from being smuggled through the bridge even if a caller computes a digest for the modified plan.

## Persistence and audit

Execution rejects any already-existing target Evidence ID. After preflight succeeds, the bridge writes the reviewed Evidence through `ClaimEvidenceRegistry`.

If a multi-entry execution fails after writes begin, newly created files from that execution are removed on a best-effort in-process rollback path.

After persistence, each Evidence record is reloaded and compared with the preview. Repository graph audit errors for newly created Evidence cause rollback. Warning-only findings such as `orphan-evidence` do not block the write because Phase 4C intentionally does not create Claim-Evidence links.

## Authority boundary

Creating literature Evidence records is not equivalent to approving a scientific Claim or accepting a support/contradiction interpretation.

Phase 4C does **not**:

- create `ClaimEvidenceLink` records;
- decide whether literature Evidence supports or contradicts a Claim;
- approve Claims or relation links;
- promote `analyst_interpretation` items;
- assert novelty;
- merge Citation records;
- retrieve or parse papers;
- invoke an LLM.

Those actions remain in separate governed workflows.

## Concurrency boundary

The bridge provides reviewed, in-process preflight and rollback semantics. It does not provide cross-process locking, crash recovery, or a transactional journal. Concurrent writers to the same Evidence identity remain a later infrastructure concern.
