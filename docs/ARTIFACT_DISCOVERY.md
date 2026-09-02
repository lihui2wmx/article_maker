# Artifact Discovery and Dry-Run Registration Planning

Phase 1C adds a bounded convenience layer above the Phase 1A manifest contract and Phase 1B filesystem registry.

Its purpose is to make the "drop research materials into the repository" workflow practical without allowing filesystem scanning to become scientific interpretation.

## 1. Scope

The discovery layer may determine only filesystem-level facts:

- which regular files exist under explicitly configured roots;
- repository-relative paths;
- deterministic media types using the Phase 1B table;
- SHA-256 checksums;
- whether a discovered path is currently unregistered, registered and unchanged, or registered with filesystem drift.

The discovery layer must not infer:

- scientific artifact kind from filename or extension;
- producer identity;
- source/derived scientific lineage;
- whether evidence is valid;
- whether a claim is supported;
- whether a file is important, novel, publishable, or suitable for a target venue.

Those meanings remain explicit higher-level inputs.

## 2. Bounded discovery policy

`DiscoveryPolicy` requires at least one explicit repository-relative root.

The repository root `.` is deliberately rejected. This prevents an accidental command from turning into an unbounded scan of project infrastructure, source packages, workflow files, and unrelated material.

Example roots may later include locations such as:

- `literature`;
- `research`;
- `experiments`;
- `theory`;
- `manuscript/figures`.

Roots must exist at execution time and may not themselves be symbolic links.

Overlapping roots are permitted. Results are deduplicated by canonical repository path and sorted lexicographically.

## 3. Ignore behavior

The default ignored directory names are:

- `.git`;
- `.venv`;
- `venv`;
- `__pycache__`;
- `build`;
- `dist`.

The default ignored file globs include common generated/transient files:

- `*.pyc`;
- `*.pyo`;
- `*.tmp`;
- `*.swp`;
- `.DS_Store`.

The active `ArtifactRegistry` manifest path is always excluded independently of user ignore patterns, preventing canonical registry records from being rediscovered as research artifacts.

Directory traversal does not follow symbolic-link directories, and symbolic-link files are not returned as candidates. This avoids path aliases and repository-boundary ambiguity.

## 4. Discovery states

Every returned `DiscoveredArtifact` has exactly one state.

### `unregistered`

No canonical artifact manifest currently binds the discovered repository path.

### `registered`

A manifest binds the same path and its deterministic media type and regular-file SHA-256 still match filesystem facts.

### `changed`

A manifest binds the path, but its stored media type or SHA-256 differs from the current file.

`changed` is an operational drift signal only. It is not a scientific judgment and Phase 1C does not silently refresh the manifest.

Missing registered paths are intentionally not represented by discovery because they are not discoverable filesystem candidates. They remain the responsibility of `ArtifactRegistry.audit()`.

## 5. Registration selections

Discovery does not automatically turn candidates into manifests.

A caller must explicitly construct a `RegistrationSelection` for every unregistered file it wants to propose for registration. The selection supplies semantic/provenance fields such as:

- `kind`;
- `producer`;
- `stage`;
- parent artifact IDs;
- optional stable artifact ID;
- title/description/tags;
- provenance command/tool/revision;
- JSON metadata.

The filesystem-derived path, media type, and checksum are not supplied by the caller.

## 6. Dry-run plan

`ArtifactDiscoverer.plan()` performs no writes.

For every explicit selection it:

1. confirms the path is inside the current discovery result;
2. requires the candidate to be `unregistered`;
3. rejects registered or changed files;
4. computes the same deterministic artifact ID used by Phase 1B when an explicit ID is absent;
5. rejects duplicate or already-bound IDs;
6. requires all declared parents to already exist in the local registry;
7. constructs a complete `ArtifactManifest` using current filesystem facts and explicit selection semantics;
8. runs normal `ArtifactManifest` validation;
9. returns the validated manifest as a `PlannedRegistration` preview.

Therefore the dry-run plan is not an approximate description. It is the exact validated manifest shape that a later execution layer could write, assuming filesystem facts remain unchanged.

## 7. No automatic batch mutation in Phase 1C

Phase 1C intentionally stops at the dry-run boundary.

It does not provide a bulk apply operation. This is deliberate because batch mutation needs additional policy for:

- stale-plan detection between review and execution;
- all-or-nothing or rollback semantics;
- parent relationships among artifacts created in the same batch;
- safe failure reporting after partial filesystem changes;
- explicit human/agent authorization of the reviewed plan.

Those concerns should be implemented as a separate bounded increment rather than hidden inside discovery.

## 8. Relationship to human authority

Discovery and planning automate mechanical inventory work. They do not consume the researcher's authority to decide what a file means.

A future AI agent may propose `RegistrationSelection` objects, but canonical scientific meaning remains reviewable because:

- the proposed semantic fields are explicit;
- the exact manifest preview is inspectable before mutation;
- changed registered files are surfaced rather than silently accepted;
- no LLM or semantic parser participates in Phase 1C.
