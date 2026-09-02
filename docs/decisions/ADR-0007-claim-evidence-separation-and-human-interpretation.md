# ADR-0007: Separate Evidence from Claim Interpretation and Keep Claim Approval Human-Governed

## Status

Accepted for Phase 3A.

## Context

The project requires a durable scientific graph in which Claims can be traced to Evidence without allowing an automated system to silently convert observations into approved scientific conclusions.

A single object that combines a Claim, its supporting material, and an approval/confidence score would collapse three materially different concepts:

1. what scientific statement is being proposed;
2. what traceable observation/source exists;
3. how that observation/source is interpreted relative to the statement.

That collapse would make conflicting evidence difficult to preserve and would weaken the human authority gates in `PROJECT.md` and `AGENTS.md`.

## Decision

Phase 3A uses three distinct canonical contracts:

- `Claim` (`clm-*`) for substantive scientific statements;
- `Evidence` (`ev-*`) for provenance-bearing observations/source statements;
- `ClaimEvidenceLink` (`cel-*`) for explicit `supports` or `contradicts` interpretations.

`Evidence` has no approval lifecycle. It must reference at least one canonical Artifact source.

`Claim` begins as `candidate`. `approved`, `rejected`, and `superseded` states require a human `Decision`.

`ClaimEvidenceLink` begins as `proposed`. `accepted`, `rejected`, and `superseded` states require a human `Decision`, because accepting an evidence-to-claim relationship is scientific interpretation rather than a mechanical indexing action.

The existing `Decision` contract is extended with `claim` and `claim_evidence_link` subject types while preserving `authority = human` in schema version 1.0.

Phase 2's repository audit remains responsible only for ResearchQuestion/Hypothesis subjects. Phase 3 subject resolution is deferred to the Phase 3 repository-level registry so architectural ownership stays explicit.

## Consequences

### Positive

- contradictory evidence can coexist without being suppressed;
- an agent may propose claims and interpretations without granting itself approval authority;
- manuscript generation can later consume only approved claims and accepted evidence relationships;
- evidence provenance remains independently inspectable;
- relation rationale is explicit rather than hidden inside an embedding score or prompt trace;
- graph/database implementations can remain derived from repository records.

### Costs

- the graph contains more records than a monolithic Claim-with-evidence object;
- human approval may be required for materially interpretive links;
- repository-level consistency logic is required in Phase 3B;
- no automatic confidence scalar is defined in v1.

## Rejected alternatives

### Store evidence directly inside Claim records

Rejected because the same Evidence can support or contradict multiple Claims and because evidence identity/provenance should survive Claim revisions.

### Treat all Artifact references as supporting evidence

Rejected because an Artifact is a container/source object; citing it does not state what observation is relevant or how it bears on a Claim.

### Let agents mark links or claims as approved based on confidence

Rejected because scientific claim acceptance and materially ambiguous evidence interpretation are explicit human authority gates.

### Use a graph database as canonical storage immediately

Rejected for Phase 3A. Canonical repository records remain the source of truth; graph materializations may be derived later.

## Follow-up

Phase 3B should add deterministic repository persistence and graph-level audit for Claim, Evidence, ClaimEvidenceLink, Decision resolution, Artifact provenance, Claim dependencies, contradiction visibility, and approved-Claim support requirements.