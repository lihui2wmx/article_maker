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

## Ready next increment — Phase 1B: deterministic artifact registration and filesystem validation

**Status:** READY after Phase 1A integration.

### Objective

Register existing repository artifacts deterministically from local paths and validate filesystem-level facts without interpreting scientific content.

### Initial boundary

Phase 1B may add deterministic path registration, file/directory existence checks, SHA-256 calculation for regular files, media-type inference with conservative fallbacks, manifest serialization/loading, and parent-ID resolution against a local registry.

It must still avoid PDF/PPT semantic parsing, embeddings, RAG, LLM calls, scientific interpretation, claim/evidence extraction, and agent orchestration.
