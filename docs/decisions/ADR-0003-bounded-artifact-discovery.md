# ADR-0003: Bounded Artifact Discovery and Dry-Run Planning

- **Status:** Accepted for Phase 1C
- **Date:** 2026-09-02

## Context

Phase 1B can register one known repository path safely, but the intended user workflow is to place heterogeneous research material into repository directories and have tooling surface what has not yet been registered.

A naive recursive scanner creates several risks:

- scanning the entire repository by accident;
- rediscovering generated registry state;
- following symlink aliases or escapes;
- silently assigning scientific meaning based on filenames/extensions;
- mutating many manifests before a human or higher-level agent can review what will happen;
- hiding changed previously registered files by automatically refreshing their checksums.

The project therefore needs discovery convenience without weakening provenance or human decision boundaries.

## Decision

### 1. Discovery is root-bounded

Discovery requires one or more explicit normalized repository-relative roots. `.` is rejected as an unbounded root.

Overlapping explicit roots are allowed and deduplicated deterministically.

### 2. Discovery returns regular files only

Phase 1C recursively discovers regular files. It does not create directory candidates, recursively hash directories, or follow symbolic links.

Directory registration remains available through the lower-level Phase 1B API when explicitly requested.

### 3. Ignore behavior is deterministic and project-owned

The implementation uses explicit ignored directory names and filename/path glob rules rather than host-specific ignore libraries or implicit global configuration.

The registry manifest directory is always excluded regardless of user policy.

### 4. Discovery state is operational

A candidate is `unregistered`, `registered`, or `changed` based only on path binding, deterministic media type, and SHA-256 comparison.

`changed` never means invalid science; it means the registered filesystem facts no longer match.

### 5. Scientific semantics remain explicit

`ArtifactKind`, producer, stage, parent lineage, and descriptive metadata are not inferred by discovery. They are supplied through explicit `RegistrationSelection` objects.

A later AI agent may propose selections, but proposals remain visible inputs rather than hidden scanner behavior.

### 6. Dry-run output is an exact manifest preview

Planning combines filesystem facts with explicit selection semantics and constructs a complete `ArtifactManifest` under normal contract validation.

This means a reviewable plan contains the exact canonical object intended for a future write, not a loosely typed task description.

### 7. Phase 1C does not implement bulk mutation

The phase stops at a no-write `BatchRegistrationPlan`.

Batch execution is deferred because a reliable apply layer needs an explicit decision about stale-plan preconditions, rollback/transaction boundaries, same-batch lineage, and authorization.

## Consequences

### Positive

- repository-drop workflows become inspectable and deterministic;
- accidental whole-repository scanning is prevented;
- registry internals cannot recursively ingest themselves;
- changed artifacts are surfaced instead of silently normalized away;
- future UI/CLI/agent layers can consume a stable discovery/plan API;
- scientific meaning remains an explicit, reviewable input;
- no LLM, parser, RAG, or external indexing dependency enters the core ingestion path.

### Negative

- users must configure roots explicitly;
- directory candidates are not bulk-discovered in this phase;
- files created by symlink aliases are ignored;
- changed artifacts require separate review/refresh handling;
- same-batch parent dependencies cannot yet be planned unless parents are already registered;
- a plan still needs a later execution mechanism before it can persist manifests.

## Deferred follow-up

A subsequent bounded phase may add reviewed plan execution with stale-plan verification and failure semantics. CLI or agent interfaces should remain thin adapters over these domain APIs rather than duplicating discovery policy.
