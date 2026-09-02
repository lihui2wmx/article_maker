# ADR-0011: Reviewed literature-to-Evidence promotion

- **Status:** Accepted
- **Date:** 2026-09-02
- **Phase:** 4C

## Context

Phase 4A/4B established canonical Citation and LiteratureNote state and deliberately separated source-reported statements from analyst interpretation. Phase 3 established Evidence as provenance-bearing scientific state and Claim-Evidence links as separately governed interpretations.

A bridge is now needed so traceable literature statements can enter the Evidence layer without collapsing these distinctions.

## Decision

### 1. Only `source_report` items are eligible

A LiteratureNote item marked `analyst_interpretation` cannot be promoted directly to `Evidence(kind=literature_statement)`.

This prevents an agent's or researcher's interpretation from being represented as though it were reported by the source publication.

### 2. Promotion is a deterministic projection

Eligible Evidence is generated mechanically from one source-report item:

- description equals the note-item text;
- Artifact and locator provenance is copied exactly;
- Citation and LiteratureNote identities are preserved in metadata;
- the Evidence ID is derived deterministically from canonical source identity and item content.

No summarization, strengthening, weakening, or scientific reinterpretation occurs in the bridge.

### 3. Planning and mutation are separated

The first operation is a dry-run `LiteratureEvidencePlan`. Planning writes no canonical Evidence.

Mutation requires an explicit `execute()` call with the digest of the exact reviewed plan.

### 4. Source records are bound to the reviewed plan

The plan stores cryptographic digests of the Citation and LiteratureNote used to build each preview. Execution reloads both records and rejects stale plans before persistence.

Execution also regenerates the expected Evidence and compares it with the reviewed preview. A caller therefore cannot alter preview text, provenance, or bridge metadata and still use the bridge as a valid source-report projection.

### 5. Evidence creation does not create scientific interpretation

The bridge creates only Evidence records. It does not create or accept Claim-Evidence links and does not approve Claims.

Whether the new Evidence supports or contradicts a Claim remains a separately governed interpretation subject to the existing human Decision boundary.

### 6. Existing Evidence identities are never overwritten

If the deterministic target Evidence ID already exists, the execution is rejected rather than silently replacing canonical scientific state.

### 7. Transaction guarantees remain bounded

The executor performs whole-plan preflight and best-effort in-process rollback of files newly created by the current execution. It does not claim cross-process serialization, crash-safe journaling, or database transaction semantics.

## Consequences

### Positive

- source statements can enter scientific state without provenance loss;
- dry-run previews are reviewable before mutation;
- stale literature records cannot silently change a reviewed promotion;
- analyst interpretation remains distinguishable from source report;
- later Claim/Evidence workflows receive deterministic literature Evidence objects.

### Costs

- a corrected LiteratureNote requires a new plan and review;
- deterministic identity means an already-promoted unchanged source item cannot be silently re-promoted or overwritten;
- cross-process concurrency remains unresolved.

## Rejected alternatives

### Automatically convert all LiteratureNote items to Evidence

Rejected because analyst interpretation is not equivalent to a source-reported statement.

### Let an LLM rewrite source-report text during promotion

Rejected because the bridge must preserve source semantics mechanically; summarization belongs in a separate reviewable transformation.

### Automatically create supporting Claim-Evidence links

Rejected because support/contradiction is an interpretation requiring its own governance.

### Overwrite an existing deterministic Evidence record

Rejected because canonical Evidence mutation must be explicit rather than a side effect of rerunning the bridge.
