# Claim and Evidence Contracts

Phase 3A defines the first canonical vocabulary for scientific statements and their evidence relationships. It is deliberately a contract-only phase: persistence, repository-wide graph resolution, extraction, retrieval, and manuscript projection remain later work.

## Contract bundle

The framework-neutral source is:

```text
schemas/claim-evidence.schema.json
```

The Python implementation is:

```text
src/article_maker/claim_evidence.py
```

Stable ID grammars are:

```text
Claim              clm-*
Evidence           ev-*
ClaimEvidenceLink  cel-*
```

## Claim

A `Claim` is a substantive scientific statement that may eventually be used in reasoning or manuscript text.

A Claim contains:

- `claim_id`;
- `research_question_id`;
- optional `hypothesis_id`;
- nonblank `statement`;
- lifecycle `status`;
- proposal attribution;
- optional human `governing_decision_id` according to lifecycle;
- optional `depends_on_claim_ids`;
- JSON metadata.

### Claim lifecycle

```text
candidate
   |
   | explicit human Decision
   v
approved / rejected / superseded
```

`candidate` means the statement may be proposed by a human or agent but is not an approved scientific conclusion.

An `approved`, `rejected`, or `superseded` Claim requires a `governing_decision_id`. A candidate Claim must not predeclare one.

This is intentionally distinct from Phase 2 `ResearchStateStatus.accepted`: accepting a research direction and approving a substantive scientific claim are different authority gates.

## Evidence

`Evidence` is a provenance-bearing record of something observed, derived, calculated, or reported. It is not itself an interpretation that a Claim is true.

Evidence kinds in v1 are:

- `experiment_result`;
- `theory_result`;
- `literature_statement`;
- `dataset_observation`;
- `analysis_result`;
- `other`.

Every Evidence record requires at least one `EvidenceSourceRef` containing a Phase 1 `Artifact` ID and an optional nonblank locator such as:

```text
page 8, Eq. (12)
results/summary.json#/failure_rate
table-2
figure-4b
```

The Artifact reference provides durable provenance. The locator narrows the relevant region without requiring content parsing in Phase 3A.

Evidence has no `approved` flag. Whether evidence supports or contradicts a Claim belongs to a separate relationship object.

## ClaimEvidenceLink

`ClaimEvidenceLink` represents an explicit interpretation between one Claim and one Evidence record.

Relations are deliberately limited to:

```text
supports
contradicts
```

A link includes a required rationale so the relationship is not represented as an unexplained edge.

### Relation lifecycle

```text
proposed
   |
   | explicit human Decision
   v
accepted / rejected / superseded
```

An agent may propose that an Evidence record supports or contradicts a Claim. That interpretation does not become canonical accepted scientific state merely because the agent wrote the link.

An accepted/rejected/superseded relation requires a human `Decision`; a proposed relation must not predeclare a Decision.

This preserves the project-level gate that materially ambiguous or conflicting evidence interpretation requires human authority.

## Human Decision extension

Phase 3A extends the existing generic `DecisionSubjectType` with:

```text
claim
claim_evidence_link
```

The existing invariant remains unchanged:

```text
authority = human
```

Subject IDs must match the corresponding `clm-*` or `cel-*` grammar.

Phase 3A only defines this object-level authority contract. Repository-level resolution of Claim and Link Decisions is deferred to Phase 3B.

## Claim dependencies

A Claim may list `depends_on_claim_ids` for logical/scientific dependencies. Exact duplicates and self-dependency are rejected by the Python validator.

Cross-record existence, cycles, and dependency semantics are repository-level constraints and therefore belong to Phase 3B.

## Validation boundary

### Phase 3A validates locally

- stable ID grammar;
- Claim lifecycle shape;
- Evidence kind and nonblank description;
- at least one Artifact-backed Evidence source;
- nonblank source locator when supplied;
- exact duplicate Evidence source rejection;
- Claim self-dependency and duplicate dependency rejection in the Python runtime;
- support/contradiction relation vocabulary;
- relation lifecycle shape;
- human-only Decision authority and Claim/Link subject ID grammar.

### Deferred to Phase 3B

- Claim -> ResearchQuestion existence;
- Claim -> Hypothesis existence and Question/Hypothesis consistency;
- Claim -> Claim dependency resolution/cycle detection;
- Evidence source Artifact existence;
- ClaimEvidenceLink -> Claim/Evidence existence;
- governing Decision existence/backlink/outcome consistency for Claims and Links;
- approved Claim support requirements;
- contradictory Evidence visibility and graph-level audits;
- canonical repository persistence layout for Claims/Evidence/Links.

## Non-goals

Phase 3A does not introduce:

- automatic extraction of Claims or Evidence;
- LLM providers or prompts;
- embeddings, vector search, or RAG;
- graph databases;
- automatic confidence scores;
- automated novelty assertions;
- experiment execution;
- manuscript generation;
- autonomous claim approval.
