# Project Charter

## Mission

`article_maker` is a repository-centric research operating system for AI-assisted scientific work. It turns heterogeneous research artifacts—papers, notes, slides, code, data, experiment outputs, figures, and manuscript drafts—into an auditable research state from which specialized AI agents can help plan research, construct arguments, write LaTeX manuscripts, review claims, and propose follow-up work.

The system optimizes for scientific quality, traceability, reproducibility, and retained human authority rather than maximum autonomous text generation.

## Core principles

1. **Repository as source of truth.** Durable project state lives in version-controlled artifacts, not in an agent's transient conversation memory.
2. **Evidence before prose.** Manuscript text must be derived from explicit claims, evidence, citations, experiment results, and approved interpretation.
3. **Provenance by default.** Important outputs should be traceable to source artifacts, code/data versions, and decisions.
4. **Human scientific authority.** Agents may inspect, propose, execute bounded tasks, critique, and draft. Humans retain approval authority over research questions, hypotheses, substantive claims, interpretation, experimental direction, and submission.
5. **Independent review.** Writing and review are separate roles and should use fresh context where practical to reduce correlated failure.
6. **Reproducibility over convenience.** Numerical results and figures should be generated from executable workflows rather than manually transcribed into manuscripts.
7. **Model/provider independence.** Domain objects and workflow state must not depend on a particular LLM vendor or agent framework.
8. **Incremental development.** Every phase has explicit exit conditions; new autonomy is added only after the underlying state model is auditable.

## Primary domain objects

The architecture will converge around a small stable vocabulary:

- **Artifact**: an input or generated research object (paper, note, code, data, figure, slide deck, result, manuscript file).
- **ResearchQuestion**: a question currently being investigated.
- **Hypothesis**: a testable or analyzable proposition.
- **Claim**: a statement that may appear in scientific reasoning or a manuscript.
- **Evidence**: an experiment, derivation, theorem, dataset observation, or external source that supports or contradicts a claim.
- **Experiment**: an executable investigation with configuration, inputs, code version, outputs, and analysis.
- **Citation**: a bibliographic source plus structured notes about its contribution and relationship to this work.
- **Decision**: a recorded human or governance decision with rationale.
- **Manuscript**: a LaTeX project generated from approved research state.
- **Review**: structured critique against scientific and venue-specific criteria.

## Human authority gates

The following actions require explicit human approval before becoming canonical project state:

- selecting or materially changing a research question;
- accepting a hypothesis as a research direction;
- approving a new substantive scientific claim;
- accepting interpretation of ambiguous or conflicting evidence;
- approving experimental direction when it materially changes the research program;
- asserting novelty against prior work;
- approving final manuscript content for submission;
- choosing a target venue and submitting externally.

Routine ingestion, indexing, formatting, consistency checks, reproducibility checks, literature summarization, draft generation, and reviewer simulation may be automated within declared permissions.

## Planned phases

### Phase 0 — Repository foundation
Define repository governance, canonical project state, directory conventions, development log, and architectural boundaries.

### Phase 1 — Artifact ingestion
Create typed artifact manifests and deterministic ingestion for local repository material.

### Phase 2 — Research state
Define questions, hypotheses, citations, decisions, and project-state schemas.

### Phase 3 — Claim and evidence graph
Implement the core claim/evidence model, provenance, validation, and human approval state.

### Phase 4 — Literature intelligence
Add bibliographic extraction, structured paper notes, citation graph construction, and novelty comparison support.

### Phase 5 — Experiment provenance
Connect experiment configurations, code revisions, outputs, tables, figures, and manuscript values.

### Phase 6 — Research planning agents
Allow agents to identify weak claims, missing evidence, high-value experiments, theoretical gaps, and literature gaps.

### Phase 7 — Scientific writing
Generate argument plans and complete LaTeX manuscript projects from approved research state and venue profiles.

### Phase 8 — Review council
Add scientific reviewer, adversarial reviewer, statistician, citation auditor, and reproducibility reviewer roles.

### Phase 9 — Venue profiles
Represent journal expectations, manuscript structure, rhetorical conventions, and quality gates without copying individual authors' prose.

### Phase 10 — Closed research/manuscript loop
Feed review findings back into structured research tasks while preserving human approval gates.

## Phase 0 exit conditions

Phase 0 is complete when:

- project mission and non-negotiable principles are documented;
- agent permissions and human gates are documented;
- canonical repository layout is documented;
- a development log records the active phase and next bounded task;
- subsequent implementation can proceed without relying on chat history for project governance.
