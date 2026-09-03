# Architecture

## Architectural thesis

`article_maker` is designed as a **repository-centric, AI-native research operating system**, not as a prompt wrapper or an application that invokes a large language model through provider APIs.

The durable system of record is structured research state stored in the repository. A capable external AI agent is expected to inspect the repository, read its operating contract, use deterministic repository tooling, modify bounded state, and leave durable handoff artifacts. Manuscripts are projections of approved scientific state into a venue-specific LaTeX representation.

The primary execution boundary is therefore **AI operates repository**, not **repository calls AI**.

## Logical layers

```text
Human researcher
      |
      | approvals / decisions
      v
Repository governance + human gates
      |
      v
External AI operator(s)
      |
      v
Repository-native workflows / deterministic tooling
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

Provides deterministic metadata lookup plus optional semantic retrieval. Any semantic/vector index is disposable and derived; deleting an index must never destroy scientific state.

### 3. Scientific state layer

Holds typed objects such as `ResearchQuestion`, `Hypothesis`, `Claim`, `Evidence`, `Citation`, `Experiment`, and `Decision`. This layer is the architectural core.

### 4. Repository workflow/tooling layer

Provides explicit state transitions, validators, audits, CLIs/APIs, reproducibility checks, build tooling, and quality gates that an external AI operator can invoke. Permission and transition semantics should be deterministic and inspectable.

### 5. AI operator layer

Specialized AI roles perform literature analysis, research planning, experiment analysis, writing, statistical review, citation auditing, reproducibility auditing, venue adaptation, and adversarial review by operating directly on repository state and following version-controlled instructions.

Different roles may be executed by different AI contexts or models, but the repository does not own or invoke those models as part of its core runtime.

### 6. Human authority layer

Humans approve high-impact scientific transitions. Approval is represented as data, not inferred from an agent's wording.

## AI-native execution contract

An AI should be able to enter the repository without prior chat history and recover enough context to continue safely. At minimum, the repository should make the following path legible and executable:

```text
read PROJECT.md
  -> read AGENTS.md
  -> read ARCHITECTURE.md + DEVELOPMENT_LOG.md
  -> inspect relevant canonical state and audits
  -> perform one bounded task
  -> validate deterministic invariants
  -> write durable state / manuscript / review artifacts
  -> update handoff state
```

The repository should therefore favor:

- explicit instructions over hidden orchestration;
- canonical files over chat memory;
- stable schemas and identifiers over prompt-only conventions;
- deterministic validators/audits over implicit agent judgment for mechanical rules;
- reviewable bounded increments over opaque autonomous loops;
- resumable handoff artifacts over session-local memory.

Prompting guidance, role instructions, workflow recipes, checklists, and manuscript templates may be stored in the repository when useful. They are operator-facing protocol artifacts, not an embedded AI service.

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
│   ├── planning_tasks/       # bounded PlanningTask records
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
├── workflows/                # repository-native workflow/instruction artifacts
├── src/article_maker/        # deterministic domain logic and tooling
├── tests/
└── .github/workflows/
```

## Canonical-state rule

Human-readable YAML/Markdown and machine-validated schemas should coexist where practical:

- YAML/JSON: structured state and manifests;
- Markdown: rationale, summaries, operating instructions, reviews, and human decisions;
- SQLite/DuckDB: derived indexes or experiment/query convenience when needed;
- graph representation: derived from canonical claim/evidence records unless a graph database is later justified;
- vector database: disposable retrieval index;
- Git history: provenance for state transitions and implementation changes.

No external database or AI-provider memory should become the only copy of research-critical state without an explicit architecture decision.

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

The exact storage representation is defined by phase-specific contracts; this document defines the semantic boundary.

## Manuscript generation model

Generation should proceed through repository-native structured intermediate representations:

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

An external AI writer should construct these artifacts directly from canonical repository state. It must not manufacture missing evidence. Unsupported narrative needs become explicit gaps or research tasks.

## Agent permission model

The initial permission model is capability-based and applies to AI operators rather than to an embedded agent runtime.

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

The implementation should remain intentionally small and repository-native:

- Python for deterministic domain logic, validation, repository operations, and reusable tooling;
- Pydantic or equivalent schema validation;
- YAML/JSON for repository state;
- Markdown for agent/human operating protocol and review artifacts;
- SQLite or DuckDB only when query/index needs justify it;
- Git for provenance, collaboration, and resumable handoff;
- LaTeX for manuscript output;
- CLI/library interfaces where they make deterministic repository operations easier for an external AI operator.

Core product functionality must not require OpenAI/Anthropic/Gemini/etc. SDKs, LLM API credentials, embedded model calls, or an agent framework such as LangChain, CrewAI, or AutoGen. Optional external wrappers may exist outside the core repository contract, but they are clients of the repository rather than part of its canonical scientific architecture.

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

- invoke AI models through a built-in provider/API layer as its primary operating model;
- embed a general-purpose autonomous-agent runtime inside the core system;
- autonomously fabricate scientific content to complete a manuscript;
- optimize primarily for stylistic imitation of individual authors;
- conceal AI involvement or provenance;
- make unreviewed autonomous submission decisions;
- place irreplaceable research state solely in embeddings, chat history, provider memory, or proprietary agent memory.

See `docs/decisions/ADR-0016-ai-native-repository-execution-model.md` for the durable decision establishing this boundary.
