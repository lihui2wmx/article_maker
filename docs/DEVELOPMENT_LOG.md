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

**Status:** ACTIVE — implementation complete; PR/remote CI review pending.

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

### Validation performed

- JSON Schema was checked against Draft 2020-12 meta-schema in an offline equivalent validation run;
- representative valid source and derived manifests passed both schema and Pydantic validation;
- representative invalid path, lineage, lifecycle, checksum, unknown-field, and non-JSON-metadata cases were rejected as intended;
- direct container cloning of GitHub was unavailable because the execution container could not resolve `github.com`; remote GitHub Actions is the canonical execution check for this branch.

### Phase 1A exit conditions

- [x] stable typed Artifact contract exists;
- [x] source vs derived provenance is explicit;
- [x] repository path escape/non-normalization is rejected;
- [x] operational lifecycle/status is explicit and scientifically non-authoritative;
- [x] representative valid/invalid contract tests exist;
- [x] material schema choices are recorded in an ADR;
- [x] implementation remains independent of RAG, parsers, LLM providers, and agent frameworks;
- [ ] pull request reviewed for bounded scope;
- [ ] remote CI passes on the branch/PR.

### Non-goals preserved

No vector database, semantic RAG, PDF/PPT parser, LLM provider, multi-agent runtime, manuscript generator, claim/evidence graph, or automatic scientific interpretation was introduced.

### Next bounded task

Open and audit the Phase 1A pull request. If CI passes and scope remains bounded, close Phase 1A and activate **Phase 1B: deterministic artifact registration and filesystem validation**. Phase 1B should register existing repository paths and compute/check deterministic metadata; it must still avoid semantic parsing and LLM interpretation.
