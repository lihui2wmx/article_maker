# Research State Registry and Consistency Audit

Phase 2B turns the Phase 2A object contracts into repository-level canonical research state.

The registry remains deliberately filesystem- and Git-native. It does not introduce a database, workflow engine, LLM, or autonomous approval mechanism.

## Canonical layout

`ResearchStateRegistry` persists one JSON record per stable identity:

```text
research/
├── questions/
│   └── rq-*.json
├── hypotheses/
│   └── hyp-*.json
└── decisions/
    └── dec-*.json
```

Each file contains the complete validated Phase 2 contract object. Serialization is deterministic UTF-8 JSON with sorted keys and a trailing newline. Writes use temporary files followed by atomic replacement of the individual target file.

This is an individual-record atomicity guarantee, not a multi-file transaction guarantee.

## Registry API

The registry exposes explicit persistence and retrieval operations:

- `save_question()` / `load_question()` / `list_questions()`;
- `save_hypothesis()` / `load_hypothesis()` / `list_hypotheses()`;
- `save_decision()` / `load_decision()` / `list_decisions()`;
- `audit()` for repository-level graph integrity.

Saving a locally valid object does not claim that the whole repository graph is coherent. Cross-object consistency is intentionally checked by `audit()`.

## Cross-object invariants

The audit resolves the following relations:

```text
Hypothesis
  -> ResearchQuestion

ResearchQuestion / Hypothesis
  -> governing Decision

Decision
  -> governed subject
  -> previous Decision

ResearchQuestion / Hypothesis / Decision
  -> ArtifactManifest
```

It reports violations instead of silently repairing them.

### Hypothesis -> ResearchQuestion

Every `Hypothesis.research_question_id` must resolve to a canonical Question record under `research/questions/`.

### Governed object -> Decision

Every `accepted`, `rejected`, or `superseded` Question/Hypothesis must resolve its `governing_decision_id`.

The resolved Decision must:

- point back to that exact object and type;
- have an outcome that maps to the object's lifecycle state.

The mapping remains:

| Decision outcome | Object status |
| --- | --- |
| `approve` | `accepted` |
| `reject` | `rejected` |
| `supersede` | `superseded` |

A proposed object must not have a governing Decision. If Decision records already target a proposed object, audit reports an unapplied/inconsistent governance state rather than inferring a transition.

## Decision history

Phase 2B extends `Decision` with optional `previous_decision_id`.

This field exists because a research question or hypothesis can receive multiple human decisions over time. Git history alone is insufficient for machine-readable current-state reasoning because a later repository snapshot should still be able to reconstruct the explicit decision sequence.

For each governed subject, Decision records must form one linear history:

```text
Decision 1
    ↓ previous_decision_id
Decision 2
    ↓
Decision 3  <- current history head
```

In JSON, the arrow is represented in the reverse direction: Decision 2 stores `previous_decision_id = Decision 1`, and Decision 3 stores `previous_decision_id = Decision 2`.

The audit rejects or reports:

- a missing previous Decision;
- previous Decision from another subject;
- a Decision timestamp that is not later than its predecessor;
- cycles;
- multiple roots for a multi-decision history;
- branching histories where one Decision has multiple successors;
- multiple current heads;
- a canonical governed object whose `governing_decision_id` does not point to the unique history head.

### No implicit transition

A newer Decision file does **not** automatically change a Question/Hypothesis status.

The canonical object must explicitly reference the current Decision head. This prevents a tool or agent from changing research direction merely by adding a Decision record.

## Artifact resolution

All `artifact_refs` on Questions, Hypotheses, and Decisions must resolve through the existing Phase 1 `ArtifactRegistry`.

Missing or contract-invalid Artifact manifests produce audit findings. The research-state registry does not mutate Artifact state.

## Malformed repository records

`audit()` is designed to continue across malformed records rather than abort the whole repository scan.

It reports, among other conditions:

- invalid JSON/contract records;
- filename/identity mismatch;
- duplicate resolved identities;
- missing Question references;
- missing Decision subjects;
- missing governing Decisions;
- Decision subject/outcome mismatch;
- missing Artifact references;
- Decision-history integrity failures.

This makes audit useful as a CI/review gate even when repository state has been manually edited.

## Authority boundary

The Phase 2A governance rule remains unchanged:

- human or agent may propose Questions and Hypotheses;
- only a `Decision` with `authority = human` may govern canonical acceptance/rejection/supersession;
- repository consistency validation proves declared structural provenance, not real-world identity authentication.

`ResearchStateRegistry` does not expose an "auto approve" operation.

## Transaction boundary

Phase 2B intentionally does not implement a multi-file decision transaction.

Updating a governed subject and creating its Decision may temporarily create an inconsistent working tree if performed as separate local writes. The repository state is considered integration-ready only when `audit()` returns no findings and the corresponding Git change is reviewed as one bounded change.

Crash-safe transaction journals, cross-process locks, and authenticated approval workflows remain future infrastructure concerns.

## Non-goals

Phase 2B does not introduce:

- Claim or Evidence objects;
- claim/evidence graph semantics;
- semantic extraction from research artifacts;
- LLM providers or prompts;
- agent orchestration;
- experiment scheduling;
- manuscript generation;
- automatic human identity verification;
- autonomous research-direction approval.
