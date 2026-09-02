# Artifact Registration and Filesystem Audit

## Purpose

Phase 1B connects real repository files and directories to the Phase 1A `ArtifactManifest` contract. Registration records filesystem-level facts only. It does not parse scientific content, infer claims, judge validity, or approve research state.

The implementation lives in `src/article_maker/registration.py`.

## Registry layout

Canonical artifact manifests are stored one file per artifact under:

```text
artifacts/manifests/<artifact_id>.json
```

The files are UTF-8 JSON serialized with sorted keys and stable indentation. Writes use a temporary file in the same directory followed by atomic replacement.

The registry is repository state, not a disposable index. Future search databases, vector stores, or graph materializations may index these manifests but must not replace them as the canonical artifact record.

## Registration inputs

A caller supplies:

- repository-relative path;
- coarse `ArtifactKind`;
- immediate `ProducerType`;
- source/derived stage when it is not a source root;
- parent artifact IDs for derived artifacts;
- optional explicit artifact ID and descriptive/provenance metadata.

The registry computes or validates:

- repository path normalization and containment;
- existence of the file or directory;
- stable generated artifact ID when no explicit ID is supplied;
- deterministic media type from the project-owned extension table;
- SHA-256 for regular files;
- `inode/directory` and no byte checksum for directories;
- parent manifest existence;
- identity/path conflicts;
- final `ArtifactManifest` contract validation.

## Generated artifact IDs

When the caller does not supply `artifact_id`, the implementation generates:

```text
art-path-<20 hex characters>
```

from a namespaced SHA-256 of the normalized initial repository path.

This has two intended properties:

1. repeated registration of the same path produces the same ID;
2. changing file bytes does not change artifact identity.

A path move is therefore treated as a new automatically identified artifact unless a caller explicitly supplies the prior ID through a future controlled move/rebind workflow. Phase 1B intentionally does not implement path rebinding because silent rebinding would weaken provenance.

Generated IDs are local identifiers within the repository. They are not intended as globally unique research identifiers.

## Re-registration semantics

Re-registering the same path with the same identity is allowed. The current filesystem facts are recomputed and the manifest is atomically replaced.

This means a modified file keeps its artifact identity while its SHA-256 changes. `audit()` can detect the change before re-registration; explicit re-registration acknowledges and records the new filesystem state.

The registry rejects ambiguous bindings:

- one path cannot be registered under two artifact IDs;
- one artifact ID cannot silently move to another path.

## Path safety

Registration accepts normalized repository-relative POSIX paths only. The registry additionally resolves filesystem paths and checks that the resolved target remains inside `repository_root`.

This second check matters for symlinks: a syntactically valid path that resolves outside the repository is rejected.

Artifact IDs are validated before they participate in manifest-path construction, including parent IDs.

## Deterministic media types

Media types use a small project-owned extension map for common research formats such as PDF, Markdown, LaTeX, BibTeX, PPT/PPTX, CSV/TSV, JSON/YAML, source code, images, NumPy/HDF5/Parquet, and archives.

Unknown file extensions use:

```text
application/octet-stream
```

Directories use:

```text
inode/directory
```

The implementation deliberately does not use the host operating system MIME database because those mappings can differ across machines and undermine deterministic manifests.

The media type is a routing hint, not scientific interpretation.

## Derived artifact parent resolution

Before a derived artifact is persisted, every `parent_artifacts` ID must resolve to an existing local manifest.

This is a local referential-integrity check only. It does not establish that the parents scientifically justify the child; claim/evidence semantics belong to later phases.

## Filesystem audit

`ArtifactRegistry.audit()` returns structured `AuditFinding` records without modifying state.

Phase 1B checks include:

- `missing-parent`: a referenced parent manifest no longer exists;
- `unsafe-path`: a stored path no longer resolves safely inside the repository;
- `missing-path`: an artifact marked `present` has disappeared;
- `status-mismatch`: an artifact marked `missing` currently exists;
- `checksum-mismatch`: current regular-file SHA-256 differs from the registered checksum.

Audit is intentionally read-only. It does not silently update status or checksums because doing so would erase the distinction between observed drift and an explicitly accepted registry update.

## Directory limitation

Phase 1B does not hash directory trees. A directory manifest records existence and media type but has no SHA-256. Recursive tree manifests or Merkle-style directory integrity may be added later if experiments require it.

## Example

```python
from pathlib import Path

from article_maker import ArtifactKind, ArtifactRegistry, ProducerType

registry = ArtifactRegistry(Path.cwd())
manifest = registry.register(
    "literature/sources/smith-2025.pdf",
    kind=ArtifactKind.PAPER,
    producer=ProducerType.EXTERNAL,
    title="Smith et al. (2025)",
)

print(manifest.artifact_id)
print(registry.audit())
```

## Non-goals

Phase 1B does not:

- parse PDF, PPT, DOCX, notebooks, source code, or datasets;
- extract text, citations, equations, claims, or experiment semantics;
- call an LLM;
- create embeddings or vector indexes;
- classify scientific importance or trustworthiness;
- approve artifacts, claims, or research decisions;
- recursively watch the filesystem or auto-register everything it sees.
