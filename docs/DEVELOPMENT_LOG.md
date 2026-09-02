# Development Log

This is the canonical handoff log for implementation state. New agents should read `PROJECT.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, then this file before changing architecture or workflow state.

## 2026-09-02 — Phase 0 repository foundation

**Branch:** `phase/0-repository-foundation`

**Status:** COMPLETE — foundation audit passed and PR #1 merged to `main`.

### Completed in this increment

- initialized the empty GitHub repository on `main`;
- created a bounded Phase 0 development branch;
- defined project mission, architectural principles, domain vocabulary, human authority gates, and phased roadmap in `PROJECT.md`;
- defined default AI agent authority, evidence discipline, change discipline, and handoff rules in `AGENTS.md`;
- documented the layered architecture, target repository layout, canonical-state rules, scientific graph semantics, manuscript-generation pipeline, permission model, and technology direction in `docs/ARCHITECTURE.md`;
- performed a read-only consistency audit across the foundation documents.

### Phase 0 audit

- **PASS — scientific authority:** human-only authority gates in `PROJECT.md` are preserved by `AGENTS.md` and the architecture permission table;
- **PASS — canonical state:** repository files and typed state are authoritative; vector search, graph materializations, and query databases remain derived/disposable unless a later architecture decision changes that boundary;
- **PASS — model independence:** no core domain object or workflow state is coupled to a particular LLM provider or agent framework;
- **PASS — evidence discipline:** prose generation is downstream of structured evidence/claims and may not fabricate missing scientific support;
- **PASS — handoff:** another agent can recover project mission, permissions, architecture, active phase, and next task from repository state alone.

### Phase 0 exit conditions

- [x] mission and non-negotiable principles documented;
- [x] human gates and agent permissions documented;
- [x] canonical repository layout documented;
- [x] development/handoff log exists;
- [x] foundation branch audited for internal consistency;
- [x] Phase 0 status explicitly closed.

### Deferred decisions

- no LLM provider or agent framework has been selected or implemented;
- no license has been selected in repository state;
- the repository intentionally contains no empty domain directories until the corresponding phase activates.

## 2026-09-02 — Phase 1A: typed artifact manifest specification

**Branch:** `phase/1a-artifact-manifest`  
**Integration carrier:** PR #2

**Status:** COMPLETE — implementation, bounded-scope audit, and remote CI gate passed.

### Objective

Define the smallest canonical representation that can describe heterogeneous repository research material without parsing, embedding, or scientifically interpreting it.

### Implemented

- added `schemas/artifact-manifest.schema.json` as the framework-neutral JSON Schema Draft 2020-12 contract;
- added Pydantic models in `src/article_maker/artifacts.py` for enforceable Python validation;
- introduced stable artifact IDs, coarse artifact kinds, explicit source/derived stage, operational lifecycle status, normalized repository paths, media type, optional SHA-256, tags, provenance, and JSON-only metadata;
- enforced source artifacts as lineage roots and required parent lineage for derived artifacts;
- rejected absolute/traversing/non-normalized paths, duplicate parents, self-parent references, malformed hashes/revisions, blank optional text, and unknown structural fields;
- explicitly separated operational status (`present`, `missing`, `superseded`) from scientific approval/confidence;
- documented the contract in `docs/ARTIFACT_MANIFEST.md`;
- recorded the durable schema decisions in `docs/decisions/ADR-0001-artifact-manifest-v1.md`;
- added contract tests covering valid source/derived manifests and representative invalid cases;
- added minimal GitHub Actions CI using official GitHub-hosted runner/actions.

### Validation and audit

- JSON Schema was checked against the Draft 2020-12 meta-schema;
- representative valid source and derived manifests passed schema and Pydantic validation;
- representative invalid path, lineage, lifecycle, checksum, unknown-field, and non-JSON-metadata cases were rejected as intended;
- `main..phase/1a-artifact-manifest` was audited as ahead-only and limited to the artifact contract, validator, docs/ADR, tests, package metadata, development log, and minimal CI;
- GitHub Actions run `33616177787` completed successfully; checkout, Python setup, install, and test steps all passed.

### Phase 1A exit conditions

- [x] stable typed Artifact contract exists;
- [x] source vs derived provenance is explicit;
- [x] repository path escape/non-normalization is rejected;
- [x] operational lifecycle/status is explicit and scientifically non-authoritative;
- [x] representative valid/invalid contract tests exist;
- [x] material schema choices are recorded in an ADR;
- [x] implementation remains independent of RAG, parsers, LLM providers, and agent frameworks;
- [x] pull request audited for bounded scope;
- [x] remote CI passes on the PR.

### Non-goals preserved

No vector database, semantic RAG, PDF/PPT parser, LLM provider, multi-agent runtime, manuscript generator, claim/evidence graph, or automatic scientific interpretation was introduced.

## 2026-09-02 — Phase 1B: deterministic artifact registration and filesystem validation

**Branch:** `phase/1b-artifact-registration`  
**Integration carrier:** PR #3  
**Integrated main commit:** `13bb43794c12fdf9a844f7e3bf1d1e462dbeac73`

**Status:** COMPLETE — implementation, bounded-scope audit, PR CI, merge, and main push CI all passed.

### Objective

Connect existing repository files/directories to canonical artifact manifests using deterministic filesystem-level registration and read-only drift auditing, without interpreting scientific content.

### Implemented

- added `ArtifactRegistry` with canonical one-manifest-per-artifact storage under `artifacts/manifests/`;
- added deterministic path-derived IDs when callers do not provide an explicit stable artifact ID;
- added repository-root containment checks in addition to syntactic path validation, including rejection of symlink escapes;
- added fixed project-owned media-type inference for common research formats with `application/octet-stream` fallback and `inode/directory` for directories;
- added streaming SHA-256 calculation for regular files;
- added parent-manifest resolution for derived artifacts and artifact-ID validation before manifest-path construction;
- added identity/path collision rules so one path cannot bind to multiple IDs and one ID cannot silently rebind to another path;
- added canonical UTF-8 JSON serialization with atomic manifest replacement;
- added read-only registry audit findings for missing parents, unsafe paths, missing present artifacts, missing-status mismatches, and file checksum drift;
- refactored path/ID validation into shared contract helpers rather than duplicating grammar in the registry;
- documented registration semantics in `docs/ARTIFACT_REGISTRATION.md`;
- recorded durable design choices in `docs/decisions/ADR-0002-artifact-registration.md`;
- added filesystem-backed tests for source/derived registration, repeat registration, directory registration, media fallback, path and symlink safety, parent resolution, identity conflicts, checksum/missing drift, missing parents, and canonical serialization.

### Validation and audit

- `main..phase/1b-artifact-registration` was audited as ahead-only and limited to artifact registration/audit runtime code, shared validators, tests, docs/ADR, and development state;
- PR CI runs `33617044290` and `33617134618` completed successfully;
- PR #3 was squash-merged into `main` at `13bb43794c12fdf9a844f7e3bf1d1e462dbeac73`;
- main push CI run `33617197177` completed successfully;
- checkout, Python setup, dependency installation, the Phase 1A contract suite, and the filesystem-backed registration suite all passed.

### Phase 1B exit conditions

- [x] existing repository files/directories can be registered into `ArtifactManifest` records;
- [x] regular-file SHA-256 is deterministic and streaming;
- [x] media-type inference is deterministic across hosts;
- [x] repository-path containment includes resolved filesystem targets;
- [x] derived parent references must resolve locally before persistence;
- [x] registry identity/path ambiguity is rejected;
- [x] manifest persistence is canonical and atomic;
- [x] read-only drift audit exists;
- [x] material registration choices are documented in ADR-0002;
- [x] bounded-scope audit passes;
- [x] remote CI passes on PR #3;
- [x] PR #3 merged and `main` push CI passes.

### Non-goals preserved

No PDF/PPT semantic parser, embedding model, vector database, RAG layer, LLM provider, agent framework, claim/evidence graph, manuscript generator, or scientific interpretation was introduced.

### Deferred within artifact ingestion

- recursive directory hashing;
- command-line registration UX;
- controlled path move/rebind while preserving identity;
- automatic operational status transitions.

## 2026-09-02 — Phase 1C: bounded artifact discovery and dry-run batch planning

**Branch:** `phase/1c-artifact-discovery`  
**Integration carrier:** PR #4  
**Integrated main commit:** `ba6e5c17585c787ab68ddd6b951dc51ebef95abf`

**Status:** COMPLETE — bounded-scope audit, PR CI, merge, and main push CI all passed.

### Objective

Make the repository-drop workflow convenient by discovering candidate research files under explicit roots, comparing them with canonical registry state, and producing exact reviewable manifest previews without semantic parsing or bulk mutation.

### Implemented

- added `DiscoveryPolicy` requiring one or more explicit normalized roots and rejecting unbounded `.` scans;
- added deterministic ignored-directory names and transient-file glob rules;
- excluded the active registry manifest directory independently of user ignore configuration;
- avoided symbolic-link roots, symbolic-link directories, and symbolic-link files to prevent alias/containment ambiguity;
- added deterministic sorted/deduplicated discovery across overlapping roots;
- added `DiscoveredArtifact` with operational states `unregistered`, `registered`, and `changed`;
- computed current deterministic MIME type and SHA-256 for discovered regular files;
- compared registered candidates against stored filesystem facts without silently refreshing drift;
- added explicit `RegistrationSelection` for kind/producer/stage/lineage and descriptive provenance semantics;
- added no-write `BatchRegistrationPlan` generation;
- made every planned action contain a complete validated `ArtifactManifest` preview using current filesystem facts;
- rejected undiscovered paths, registered paths, changed paths, duplicate selections, unavailable parents, duplicate/plausibly colliding IDs, and invalid manifest semantics before any write;
- documented discovery/planning semantics in `docs/ARTIFACT_DISCOVERY.md`;
- recorded durable bounded-discovery choices in `docs/decisions/ADR-0003-bounded-artifact-discovery.md`;
- added filesystem-backed tests covering roots, ignores, ordering/deduplication, registry exclusion, registered/changed states, symlink behavior, exact dry-run manifests, parent resolution, collision handling, and invalid semantic inputs.

### Validation and audit

- `main..phase/1c-artifact-discovery` was audited as ahead-only and limited to discovery/planning runtime code, exports, tests, docs/ADR, and development state;
- PR #4 CI runs `33618851340` and `33618942858` completed successfully, including the latest head `a2a6f8cce2d371a9262536bb58f142b02cb9b092`;
- PR #4 was squash-merged into `main` at `ba6e5c17585c787ab68ddd6b951dc51ebef95abf`;
- main push CI run `33619011090` completed successfully;
- checkout, Python setup, dependency installation, existing artifact contract/registration tests, and the new discovery/planning suite all passed.

### Phase 1C exit conditions

- [x] discovery requires bounded explicit roots;
- [x] default ignore behavior is deterministic and project-owned;
- [x] registry state cannot rediscover itself;
- [x] discovery does not follow symbolic links;
- [x] overlapping roots produce deterministic deduplicated output;
- [x] registered/unregistered/changed state is explicit;
- [x] discovery does not infer scientific artifact kind or provenance semantics;
- [x] dry-run plans produce exact contract-validated manifest previews;
- [x] planning performs no manifest writes;
- [x] changed registered files require explicit review rather than silent refresh;
- [x] ADR and documentation define the bounded authority model;
- [x] bounded-scope audit passes;
- [x] remote PR CI passes;
- [x] integration merged and main push CI passes.

### Non-goals preserved

No content parsing, PDF/PPT extraction, embeddings, RAG, vector database, LLM provider, agent orchestration, claim/evidence extraction, manuscript generation, or scientific interpretation was introduced.

### Explicitly deferred

- batch-plan execution/mutation;
- stale-plan verification between review and apply;
- rollback/all-or-nothing semantics;
- same-batch parent dependencies;
- CLI/UX adapters;
- changed-artifact refresh workflow;
- directory candidate discovery and recursive directory hashing.

## Ready next increment — Phase 1D: reviewed batch-plan execution

**Status:** READY after Phase 1C integration.

### Objective

Execute an already-reviewed `BatchRegistrationPlan` safely while verifying that filesystem facts have not changed since planning and defining explicit failure/rollback semantics.

The execution layer must remain a mechanical ingestion capability and must not introduce semantic parsing or scientific interpretation.
