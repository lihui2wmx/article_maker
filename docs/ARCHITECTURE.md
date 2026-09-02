# Architecture

## Architectural thesis

`article_maker` is designed as a **repository-centric research operating system**, not as a prompt wrapper around a large language model.

The durable system of record is structured research state stored in the repository. AI agents operate over that state through bounded workflows. Manuscripts are projections of approved scientific state into a venue-specific LaTeX representation.

## Logical layers

```text
Human researcher
      |
      | approvals / decisions
      v
Workflow and human gates
      |
      v
Specialized agents
      |
      v
Research state / claim-evidence graph / decision log
      |
      v
Retrieval and indexing
      |
      v
Repository artifacts
      |
      v
Execution environment (code, experiments, LaTeX, CI)
```

### 1. Repository artifact layer

Stores source material and generated durable artifacts: literature, notes, slides, code, datasets or dataset manifests, experiment outputs, figures, theory notes, manuscript sources, and reviews.

### 2. Retrieval/index layer

Provides deterministic metadata lookup plus semantic retrieval. Vector search is an index, not the canonical store. Deleting an index must never destroy scientific state.

### 3. Scientific state layer

Holds typed objects such as `ResearchQuestion`, `Hypothesis`, `Claim`, `Evidence`, `Citation`, `Experiment`, and `Decision`. This layer is the architectural core.

### 4. Workflow layer

Runs explicit state transitions and quality gates. Workflows should be inspectable and deterministic around permissions even when individual model calls are probabilistic.

### 5. Agent layer

Specialized roles perform literature analysis, research planning, experiment analysis, writing, statistical review, citation auditing, reproducibility auditing, venue adaptation, and adversarial review.

### 6. Human authority layer

Humans approve high-impact scientific transitions. Approval is represented as data, not inferred from an agent's wording.

## Canonical repository layout

The target layout is intentionally broader than the current implementation. Directories should be introduced when their phase becomes active rather than populated with empty placeholders.

```text
article_maker/
├── README.md
├── PROJECT.md
├── AGENTS.md
├── docs/
│   ├── ARCHITECTURE.md
│   └── DEVELOPMENT_LOG.md
├── schemas/                  # typed canonical state definitions
├── research/
│   ├── questions/
│   ├── hypotheses/
│   ├── decisions/
│   └── logs/
├── literature/
│   ├── sources/
│   ├── metadata/
│   └── notes/
├── artifacts/                # normalized manifests for heterogeneous inputs
├── claims/                   # canonical claims and claim metadata
├── evidence/                 # evidence records / graph materialization
├── experiments/
│   └── <experiment-id>/
├── theory/
├── journals/                 # venue profiles and constraints
├── manuscript/
│   ├── main.tex
│   ├── sections/
│   ├── figures/
│   ├── tables/
│   ├── bibliography/
│   └── supplementary/
├── reviews/
├── workflows/
├── src/article_maker/
├── tests/
└── .github/workflows/
```

## Canonical-state rule

Human-readable YAML/Markdown and machine-validated schemas should coexist where practical:

- YAML/JSON: structured state and manifests;
- Markdown: rationale, summaries, and human decisions;
- SQLite/DuckDB: derived indexes or experiment/query convenience when needed;
- graph representation: derived from canonical claim/evidence records unless a graph database is later justified;
- vector database: disposable retrieval index;
- Git history: provenance for state transitions and implementation changes.

No external database should become the only copy of research-critical state without an explicit architecture decision.

## Core graph

The scientific model should support relationships equivalent to:

```text
ResearchQuestion
  -> Hypothesis
      -> Claim
          -> supported_by -> Evidence
          -> contradicted_by -> Evidence
          -> depends_on -> Claim
          -> cites -> Citation
          -> appears_in -> Manuscript location

Evidence
  -> produced_by -> Experiment / Theory / Source
  -> provenance -> code/data/config/version
```

The exact storage representation will be defined during Phase 3; this document defines the semantic boundary only.

## Manuscript generation model

Generation should proceed through structured intermediate representations:

```text
approved claims + evidence + citations + venue profile
                    |
                    v
             argument plan
                    |
                    v
              section plan
                    |
                    v
             paragraph intent
                    |
                    v
                LaTeX draft
                    |
                    v
     claim/citation/numeric/review audits
```

A writer should not manufacture missing evidence. Unsupported narrative needs become explicit gaps or research tasks.

## Agent permission model

The initial permission model is capability-based rather than framework-specific.

| Role | Read artifacts | Propose research | Execute bounded analysis | Edit manuscript | Approve scientific claims | Submit |
|---|---:|---:|---:|---:|---:|---:|
| Literature agent | yes | yes | yes | no | no | no |
| Research planner | yes | yes | yes | no | no | no |
| Experiment agent | yes | yes | yes | no | no | no |
| Writer | yes | no | no | yes | no | no |
| Reviewer | yes | yes | yes | no | no | no |
| Reproducibility auditor | yes | no | yes | no | no | no |
| Human researcher | yes | yes | yes | yes | yes | yes |

Implementation may refine permissions but must preserve the human-only authority gates in `PROJECT.md`.

## Technology direction

The initial implementation should remain intentionally small:

- Python for orchestration and domain logic;
- Pydantic or equivalent schema validation;
- YAML/JSON for repository state;
- SQLite or DuckDB only when query/index needs justify it;
- Git for provenance and collaboration;
- LaTeX for manuscript output;
- provider adapters around LLM APIs rather than provider-specific domain models.

An agent framework may be added later as an adapter. Core domain objects, permissions, and workflow transitions must not depend on LangChain, CrewAI, AutoGen, or any single provider.

## Quality architecture

The mature system should support quality gates for at least:

1. schema/build validity;
2. citation integrity;
3. claim-to-evidence support;
4. experiment/numeric consistency;
5. reproducibility;
6. statistical validity where applicable;
7. novelty/literature coverage;
8. independent scientific review;
9. adversarial review;
10. human final approval.

## Architectural non-goals

The project is not intended to:

- autonomously fabricate scientific content to complete a manuscript;
- optimize primarily for stylistic imitation of individual authors;
- conceal AI involvement or provenance;
- make unreviewed autonomous submission decisions;
- place irreplaceable research state solely in embeddings, chat history, or proprietary agent memory.
