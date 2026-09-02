# ADR-0008: Keep Claim/Evidence JSON Canonical and Separate Structural Errors from Scientific Warnings

## Status

Accepted for Phase 3B.

## Context

Phase 3A defined typed `Claim`, `Evidence`, and `ClaimEvidenceLink` contracts, but object-level validation cannot establish repository truth. A syntactically valid Claim can reference a missing ResearchQuestion, a valid Evidence record can reference an unavailable Artifact, and a valid accepted relation can point at a missing Claim or Evidence record.

The repository also needs to expose scientifically important states that are not equivalent to schema corruption. In particular:

- an approved Claim may temporarily lack accepted supporting Evidence;
- accepted supporting and contradicting Evidence may coexist;
- Evidence may be recorded before any Claim relationship exists.

Treating those conditions as automatic invalidation would let mechanical audit logic overrule human scientific authority. Hiding them would weaken research guidance and adversarial review.

## Decision

Phase 3B introduces `ClaimEvidenceRegistry` with canonical JSON records at:

```text
claims/<claim-id>.json
evidence/<evidence-id>.json
evidence/links/<link-id>.json
```

ResearchQuestion, Hypothesis, Decision, and Artifact records remain owned by their existing canonical repositories and are resolved as external graph nodes.

The registry provides deterministic typed save/load/list operations and a malformed-record-tolerant read-only audit.

Audit findings are explicitly classified as:

- `error` for broken referential integrity, malformed records, Claim dependency cycles, or Decision/governance inconsistency;
- `warning` for scientifically meaningful gaps or conflicts that require attention but do not authorize automatic lifecycle changes.

The first warning cases are:

- approved Claim without accepted supporting Evidence;
- simultaneous accepted supporting and contradicting Evidence;
- Evidence not yet linked to any Claim.

Decision histories for Claim and ClaimEvidenceLink subjects must remain linear and explicit. A governed object must point to the unique Decision-history head; timestamps or file creation order never implicitly determine current scientific state.

## Consequences

### Positive

- repository state becomes queryable and auditable without introducing a graph database as canonical storage;
- Claim/Evidence provenance can be validated across Phase 1, Phase 2, and Phase 3 boundaries;
- contradictory Evidence remains visible rather than being silently filtered;
- support gaps can drive future research-planning tasks without revoking human approval;
- malformed files do not hide unrelated integrity problems;
- later manuscript gates can distinguish structural corruption from scientific warnings.

### Costs

- repository audit code must resolve multiple canonical directories;
- Decision-history validation is repeated at the Phase 3 domain boundary rather than hidden behind a database constraint;
- per-record atomic writes do not provide multi-file transaction semantics;
- warning policy requires later workflows to decide which warnings block specific actions such as manuscript release.

## Rejected alternatives

### Make a graph database the canonical store

Rejected. It would introduce an additional critical state system before query scale justifies it and would weaken Git-native review/provenance.

### Automatically downgrade an approved Claim when support is missing

Rejected. Claim approval is a human scientific authority gate. Audit may surface the gap but must not reverse the Decision.

### Collapse contradictory Evidence into a confidence score

Rejected. A scalar would hide the underlying accepted support/contradiction records and encourage premature automated adjudication.

### Treat orphan Evidence as an error

Rejected. Evidence can legitimately be recorded before a scientific interpretation is proposed.

## Follow-up

A later bounded phase may add derived graph/query indexes and research-planning views over these findings. Such indexes must remain reconstructable from canonical repository records.
