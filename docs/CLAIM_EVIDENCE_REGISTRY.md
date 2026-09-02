# Claim/Evidence Repository Registry

## Purpose

Phase 3B turns the Phase 3A `Claim`, `Evidence`, and `ClaimEvidenceLink` contracts into repository-level scientific graph state.

The repository remains canonical. The registry persists typed JSON records and performs read-only graph audits; it does not infer, approve, repair, rank, or suppress scientific interpretations.

## Canonical locations

```text
claims/<claim-id>.json
evidence/<evidence-id>.json
evidence/links/<link-id>.json
research/questions/<research-question-id>.json
research/hypotheses/<hypothesis-id>.json
research/decisions/<decision-id>.json
artifacts/manifests/<artifact-id>.json
```

`ClaimEvidenceRegistry` owns the first three locations and resolves the remaining locations as external canonical state.

## Persistence API

The registry provides typed operations:

- `save_claim` / `load_claim` / `list_claims`;
- `save_evidence` / `load_evidence` / `list_evidence`;
- `save_link` / `load_link` / `list_links`.

Each record is serialized as deterministic UTF-8 JSON with sorted keys and a trailing newline. A single record replacement uses an in-directory temporary file followed by `os.replace`.

This provides per-record atomic replacement. It is not a multi-record transaction and does not provide cross-process locking.

## Audit model

`ClaimEvidenceRegistry.audit()` is read-only and malformed-record tolerant. An invalid JSON/model file is reported without preventing unrelated graph checks from running.

Findings have two severities:

- `error` — repository graph integrity is broken or governance references are inconsistent;
- `warning` — scientific support/conflict state deserves attention but does not authorize the audit layer to reverse a human decision.

### Structural checks

The audit resolves:

- Claim -> ResearchQuestion;
- optional Claim -> Hypothesis;
- Hypothesis -> the same ResearchQuestion named by the Claim;
- Claim -> dependent Claims;
- Claim dependency cycles;
- Evidence -> Artifact sources;
- ClaimEvidenceLink -> Claim;
- ClaimEvidenceLink -> Evidence;
- Claim/Link -> governing Decision;
- Decision -> Claim/Link backlink;
- Decision outcome -> Claim/Link lifecycle;
- Decision predecessor, ordering, branching, cycles, roots, heads, and stale governing references.

Missing references, malformed records, identity mismatches, dependency cycles, and governance inconsistencies are errors.

## Scientific-state warnings

Some audit results are deliberately warnings rather than errors.

### Approved Claim without accepted support

An approved Claim with no `accepted` `supports` link to available Evidence emits:

```text
approved-claim-without-accepted-support
```

This warning does not revoke Claim approval. Human authority remains canonical; the warning exposes a support gap for review, research planning, or later manuscript gating.

### Accepted supporting and contradicting Evidence

If one Claim simultaneously has accepted supporting and accepted contradicting links, the audit emits:

```text
accepted-evidence-conflict
```

Both sides remain present in canonical state. The system must not suppress inconvenient Evidence or automatically select a winner.

### Orphan Evidence

Evidence that is not referenced by any ClaimEvidenceLink emits:

```text
orphan-evidence
```

This is informational scientific-state debt rather than structural corruption. Evidence may legitimately be recorded before a Claim relationship is proposed.

## Governance boundary

The registry never changes scientific lifecycle fields while auditing.

Agents may create candidate Claims, Evidence records, and proposed ClaimEvidenceLinks under authorized workflows. Human `Decision` records remain required for substantive Claim transitions and accepted/rejected/superseded evidence interpretations.

A newer Decision file does not silently change canonical state. A governed Claim or ClaimEvidenceLink must explicitly reference the unique head of its Decision history.

## Derived graph policy

The JSON records above are the source of truth. A graph database, SQLite/DuckDB index, vector store, or in-memory graph may later materialize these relationships for query performance, but deleting such a derived representation must not destroy scientific state.

## Explicit non-goals

Phase 3B does not implement:

- PDF/PPT/literature semantic extraction;
- LLM or model provider abstraction;
- agent orchestration;
- semantic retrieval or embeddings;
- automatic confidence/evidence-strength scoring;
- automatic resolution of contradictory evidence;
- novelty assertions;
- manuscript generation;
- experiment execution;
- crash-safe multi-file transactions or cross-process locks.
