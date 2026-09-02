# ADR-0001: Artifact Manifest v1 Contract

**Status:** Accepted for Phase 1A  
**Date:** 2026-09-02

## Context

`article_maker` must ingest heterogeneous research material without making the canonical research state depend on a parser, vector database, LLM provider, agent framework, or Python implementation. The first durable contract therefore needs to describe artifacts before any content interpretation occurs.

The contract also needs enough provenance to distinguish raw/source material from generated material while preserving the project's human scientific-authority boundary.

## Decision

1. **JSON Schema Draft 2020-12 is the language-independent external contract.**
   `schemas/artifact-manifest.schema.json` defines the portable v1.0 representation.

2. **Pydantic is an initial validator, not the canonical storage technology.**
   `src/article_maker/artifacts.py` mirrors the contract and enforces semantic invariants that standard JSON Schema cannot express cleanly, such as rejecting self-parent lineage.

3. **Artifacts use stable IDs independent of file names and paths.**
   Renaming or relocating a payload must not require changing its scientific identity.

4. **Repository paths are normalized, repository-relative POSIX paths.**
   Absolute paths, traversal segments, platform-specific separators, repeated separators, and trailing slashes are rejected. This keeps manifests portable and prevents path escape.

5. **Lineage is explicit through `stage` and `parent_artifacts`.**
   A `source` artifact is a lineage root and has no parents. A `derived` artifact must identify at least one registered parent artifact.

6. **Artifact `status` is operational only.**
   `present`, `missing`, and `superseded` describe payload availability/lifecycle. They do not encode scientific confidence, approval, novelty, claim validity, or publication readiness.

7. **`metadata` is restricted to JSON-compatible values and is non-canonical for durable domain semantics.**
   Important scientific concepts must become typed objects in later phases instead of accumulating in arbitrary metadata.

8. **The manifest remains intentionally coarse.**
   Bibliographic identity, experiment parameters, claims, evidence, decisions, statistical analysis, venue constraints, and manuscript approval are out of scope for Artifact v1.

## Consequences

### Positive

- ingestion can begin without choosing an AI or retrieval stack;
- all later objects can reference stable artifact IDs;
- generated AI/experiment material has auditable parent lineage;
- repository relocation and cross-platform use remain possible;
- operational artifact status cannot silently become a substitute for human scientific approval.

### Costs and limitations

- registering a derived artifact requires parent manifests to exist conceptually before full graph validation is implemented;
- JSON Schema alone cannot reject self-parent references, so semantic validation remains necessary;
- the coarse `kind` enum may require versioned extension later;
- Phase 1A validates path syntax but does not yet check filesystem existence, calculate hashes, detect media types, or validate that parent IDs resolve.

## Deferred to Phase 1B+

- deterministic repository scanning and manifest creation;
- filesystem existence and checksum verification;
- media-type detection;
- parent-ID resolution against an artifact registry;
- duplicate-content detection;
- parser selection and normalized extracted-content artifacts;
- any semantic retrieval or LLM-based interpretation.
