# Development Log

This is the canonical handoff log for implementation state. New agents should read `PROJECT.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, then this file before changing architecture or workflow state.

## 2026-09-02 — Phase 0 repository foundation

**Branch:** `phase/0-repository-foundation`

**Status:** COMPLETE — foundation audit passed.

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

- no application/runtime code exists yet;
- no schemas exist yet;
- no artifact-ingestion pipeline exists yet;
- no LLM provider or agent framework has been selected or implemented;
- no license has been selected in repository state;
- the repository intentionally contains no empty domain directories until the corresponding phase activates.

## Active next increment — Phase 1A: typed artifact manifest specification

**Status:** READY

### Objective

Define the smallest canonical representation that can describe heterogeneous repository research material without parsing or embedding it yet.

### Required outputs

- an `Artifact` schema with stable identity, artifact kind, repository path, media/format metadata, provenance, lifecycle/status, and optional human description;
- explicit distinction between source artifacts and generated/derived artifacts;
- validation rules that prevent paths outside the repository and ambiguous provenance;
- representative valid/invalid fixtures or examples sufficient to review the contract;
- a short decision record for any schema choice that materially constrains later ingestion.

### Non-goals for Phase 1A

Do not add vector databases, semantic RAG, PDF/PPT parsing, LLM providers, multi-agent runtimes, manuscript generation, claim/evidence graphs, or automatic scientific interpretation in this increment.

### Next bounded task

Implement and review the Phase 1A artifact-manifest contract. Prefer a framework-neutral schema first; introduce Python/Pydantic runtime code only if it adds enforceable validation that JSON Schema alone cannot express cleanly.
