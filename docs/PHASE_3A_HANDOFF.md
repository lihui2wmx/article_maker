# Phase 3A Handoff Snapshot

Phase 3A defines framework-neutral `Claim`, `Evidence`, and `ClaimEvidenceLink` contracts with explicit human-governed approval/interpretation boundaries.

Implemented:

- `clm-*`, `ev-*`, `cel-*` IDs;
- `Claim` lifecycle: candidate/approved/rejected/superseded;
- `Evidence` with Artifact-backed provenance and no approval lifecycle;
- `ClaimEvidenceLink` with supports/contradicts relation and proposed/accepted/rejected/superseded lifecycle;
- `Decision` subject types for claim and claim_evidence_link, human authority unchanged;
- Python and Draft 2020-12 contracts;
- Phase 2 registry compatibility guard;
- tests, docs, and ADR-0007.

Deferred to Phase 3B: repository persistence and graph-level cross-object audit for Claims/Evidence/Links, Claim dependency cycles, Artifact resolution, Decision backlinks/history, contradiction visibility, and approved-Claim support requirements.
