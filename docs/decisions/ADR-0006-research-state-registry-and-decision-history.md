# ADR-0006: Repository research-state registry and linear Decision history

- **Status:** Accepted
- **Date:** 2026-09-02
- **Phase:** 2B

## Context

Phase 2A introduced object-level contracts for `ResearchQuestion`, `Hypothesis`, and human `Decision` records. Those contracts intentionally could not prove whether references resolve against repository state.

Phase 2B needs a durable repository representation that can answer questions such as:

- Does a Hypothesis point to an existing ResearchQuestion?
- Does an accepted Question point to a real human Decision?
- Does that Decision point back to the same subject?
- Does Decision outcome match lifecycle status?
- Do supporting Artifact references exist?
- If a subject has several Decisions over time, is the history coherent and which Decision is current?

The design must preserve the existing rule that adding a file or running an agent may not silently approve or redirect research.

## Decision

### 1. Persist canonical research state as one JSON file per object

Use deterministic repository locations:

```text
research/questions/<rq-id>.json
research/hypotheses/<hyp-id>.json
research/decisions/<dec-id>.json
```

These JSON files remain the canonical research-state representation. No external database is required for correctness.

### 2. Use `ResearchStateRegistry` as a thin filesystem integrity layer

The registry provides deterministic serialization, per-record atomic replacement, typed loading/listing, and repository-level audit.

It must not embed research planning, semantic inference, LLM calls, or automatic approval logic.

### 3. Cross-object validity belongs to repository audit

Pydantic/JSON Schema continue to enforce local object shape. `ResearchStateRegistry.audit()` resolves repository-level invariants.

This avoids constructors with hidden filesystem dependencies and preserves framework-neutral contract semantics.

### 4. Extend Decision with optional `previous_decision_id`

A subject may receive several human Decisions during its lifetime. The canonical repository snapshot should retain explicit, machine-readable Decision order instead of relying only on Git chronology or timestamps.

`previous_decision_id` points from a newer Decision to the immediately preceding Decision for the same subject.

The field is optional so the first Decision remains valid and existing Phase 2A records remain backward compatible.

### 5. Decision history must be linear

For each subject, audit requires Decision history to be a single chain rather than a branch or DAG.

It reports:

- missing predecessors;
- predecessor subject mismatch;
- non-increasing decision timestamps;
- cycles;
- multiple roots in a multi-decision history;
- multiple successors from one Decision;
- multiple heads.

A linear chain is chosen because concurrent/conflicting human decisions require explicit resolution rather than automatic merge semantics.

### 6. Current state is explicit, not inferred from newest Decision

The governed Question/Hypothesis must explicitly set `governing_decision_id` to the unique Decision-history head.

The registry must not infer current research direction from filesystem modification time, Git commit order, or the latest `decided_at` timestamp.

This prevents a newly written Decision file from silently changing canonical research direction.

### 7. Artifact references resolve through the Phase 1 ArtifactRegistry

Questions, Hypotheses, and Decisions may reference Artifact IDs, but those IDs must resolve to canonical Artifact manifests during repository audit.

No research-state operation may silently create, refresh, or reinterpret Artifact provenance.

### 8. Audit reports malformed records without aborting the whole scan

Manual repository editing is expected in a Git-native system. One malformed file must not prevent audit from reporting other integrity problems.

The audit therefore emits structured findings for invalid records and continues where possible.

## Consequences

### Positive

- research state is fully inspectable in Git;
- human approval records remain explicit and auditable;
- cross-object integrity is mechanically testable;
- Decision history can be reconstructed from one repository snapshot;
- conflicting Decision branches become visible instead of being guessed away;
- no database or agent framework becomes architectural infrastructure.

### Costs

- a multi-file human decision update can temporarily produce an inconsistent working tree;
- Decision history requires explicit predecessor maintenance;
- one-file-per-record scanning is adequate for current scale but not optimized for very large registries;
- real-world authentication of `decided_by` remains outside this layer.

## Rejected alternatives

### Store only the latest Decision

Rejected because it discards machine-readable governance history from the current repository snapshot and over-relies on Git archaeology.

### Treat the most recent timestamp as automatically governing

Rejected because timestamp ordering is not equivalent to explicit human authorization of the current canonical state.

### Allow branching Decision graphs and automatically select a winner

Rejected because conflict resolution is a substantive governance action. The system should surface the conflict to a human rather than invent precedence rules.

### Put all research state in SQLite first

Rejected for Phase 2B because repository JSON is easier to inspect, review, diff, and preserve as canonical state. A derived query index may be added later if scale justifies it.

### Resolve references inside Pydantic constructors

Rejected because object construction would become filesystem-dependent and framework-neutral contracts would no longer represent local validity cleanly.

## Follow-up

After Phase 2B, the next bounded step should define the first Claim/Evidence contracts and their relationship to accepted research state. That phase must preserve the same separation between candidate scientific statements, evidence, and human approval.
