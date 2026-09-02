# ADR-0002: Deterministic Artifact Registration

- **Status:** Accepted
- **Date:** 2026-09-02
- **Phase:** 1B

## Context

Phase 1A defined the framework-neutral `ArtifactManifest` contract. Phase 1B needs to connect that contract to actual repository files without introducing semantic parsing, model calls, or an external database.

Registration must be reproducible across developer machines and must not blur filesystem observations with scientific interpretation.

## Decision

### 1. Canonical manifests are repository JSON files

Each artifact is persisted as one canonical JSON file at:

```text
artifacts/manifests/<artifact_id>.json
```

The registry files remain version-controllable, inspectable, and independent of any later query/index technology.

### 2. Automatic IDs are derived from normalized initial paths

When no ID is provided, the registry generates a namespaced SHA-256-derived ID from the normalized repository-relative path.

Content hashes are not used as identity because research artifacts may legitimately change while retaining identity. A file move is not silently interpreted as the same artifact; preserving identity across moves requires an explicit future workflow.

### 3. Filesystem facts are computed; scientific roles are supplied

The registry computes path containment, existence, media type, file SHA-256, and operational `present` status.

The caller remains responsible for `ArtifactKind`, `ProducerType`, and derived-parent declarations. These are not inferred from file extensions because doing so would turn transport-level heuristics into canonical research semantics.

### 4. Media-type inference uses a project-owned fixed table

The implementation does not use the host MIME database. A fixed table provides consistent values for supported research file extensions, while unknown extensions fall back to `application/octet-stream`.

This trades breadth for reproducibility.

### 5. Derived parents must already exist locally

Every parent ID is validated and must resolve to an existing artifact manifest before the derived manifest is persisted.

This is referential integrity only; it does not imply scientific evidentiary support.

### 6. Registration updates are explicit and audit is read-only

Re-registering the same identity/path recomputes current filesystem facts and atomically replaces the manifest. `audit()` observes drift but never repairs it automatically.

This preserves an auditable distinction between detected change and accepted registry state.

### 7. Directory integrity is deferred

Directories are registerable as `inode/directory`, but Phase 1B does not recursively hash directory trees. Tree integrity can be introduced later if experiment provenance needs it.

## Consequences

### Positive

- artifact state remains Git-native and human-readable;
- repeated registration is deterministic;
- host-specific MIME differences do not alter manifests;
- byte-level drift in regular files is detectable;
- parent references have local referential integrity;
- no external database or LLM runtime becomes foundational.

### Tradeoffs

- moving a path changes an automatically generated ID unless the caller explicitly preserves identity in a later controlled workflow;
- the fixed media map will need deliberate extension for new formats;
- directory content drift is not detected in this phase;
- registration still requires a caller to provide coarse artifact role/provenance rather than attempting automatic classification.

## Rejected alternatives

### Content-hash-as-artifact-ID

Rejected because any legitimate edit would create a new identity and make longitudinal provenance cumbersome.

### Random UUID on every registration

Rejected because repeated registration of the same unregistered path would not be deterministic.

### Host `mimetypes` database

Rejected because mappings can vary across operating systems and installations.

### SQLite as the canonical registry

Rejected at this phase because JSON manifests provide sufficient scale while remaining directly reviewable and version-controlled. A database may later be introduced as a derived query index.

### Automatic extension-based scientific classification

Rejected because extension identifies representation, not scientific role. A JSON file may be an experiment configuration, output, dataset metadata, or unrelated material.
