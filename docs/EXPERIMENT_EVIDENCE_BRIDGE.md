# Reviewed Experiment-to-Evidence Bridge

## Purpose

Phase 5C provides a deterministic, reviewable bridge from explicitly selected `ExperimentRun` output or diagnostic Artifacts into canonical `Evidence` records.

It does **not** infer what an experiment means scientifically. The bridge records selected execution provenance as Evidence material and leaves support/contradiction, significance, correctness, reproduction success, and Claim governance to later workflows and human review.

## Source boundary

A selection contains exactly:

- `experiment_id`;
- `run_id`;
- `artifact_id`;
- optional precise `locator`.

The selected Artifact must be present in exactly one of the referenced Run's provenance roles:

- `output_artifact_ids`; or
- `termination.diagnostic_artifact_ids`.

An Artifact absent from both roles is ineligible. An Artifact present in both roles is rejected as ambiguous rather than assigned a role heuristically.

## Canonical projection

For an output Artifact, the preview uses:

- `Evidence.kind = experiment_result`.

For a termination diagnostic Artifact, the preview uses:

- `Evidence.kind = other`.

The latter prevents a failed-run log or diagnostic file from being mislabeled as an experimental result.

The Evidence description is mechanical and contains only Run ID, provenance role, Artifact ID, and optional locator. The bridge does not accept free-form scientific interpretation as part of the projection.

`recorded_by` is inherited from the Run's `executed_by` attribution.

Each Evidence record contains one exact `EvidenceSourceRef` for the selected Artifact and optional locator.

## Traceability metadata

The `experiment_bridge` metadata records:

- Experiment ID;
- Run ID;
- Run's `experiment_spec_digest`;
- operational Run status;
- Artifact ID;
- derived provenance role (`output` or `diagnostic`);
- locator;
- exact Run-record digest;
- exact Artifact-manifest digest.

These fields are provenance facts. They are not scientific interpretations.

## Deterministic identity

Generated Evidence IDs use:

```text
ev-exp-<24 hex characters>
```

The digest input includes bridge version, Experiment ID, Run ID, Artifact ID, provenance role, and locator.

The same exact selection therefore maps to the same Evidence ID.

## Planning

`ExperimentEvidenceBridge.plan()` is read-only.

Planning validates:

1. the Experiment exists and validates;
2. the Run exists and validates;
3. the Run belongs to the Experiment;
4. the Run's stored `experiment_spec_digest` matches the current canonical Experiment;
5. the selected Artifact has exactly one eligible Run provenance role;
6. the Artifact manifest exists;
7. the selected Artifact currently passes ArtifactRegistry audit, including checksum/path drift;
8. the generated Evidence ID is not already occupied;
9. duplicate exact selections are rejected.

The returned `ExperimentEvidencePlan` contains complete Evidence previews and snapshot digests. Planning writes no Evidence files.

## Review binding

`experiment_evidence_plan_digest()` hashes the complete plan, including:

- source identities;
- provenance role;
- Experiment snapshot digest;
- Run snapshot digest;
- Artifact-manifest digest;
- complete Evidence preview.

`execute()` requires the exact reviewed digest. A changed plan is rejected.

## Stale and tamper protection

Before any Evidence write, execution reloads the canonical Experiment, Run, and Artifact provenance and verifies the reviewed snapshots.

Execution also regenerates the expected Evidence preview from the current source records and requires exact equality with the reviewed preview.

Consequently, changing the preview and merely recomputing the plan digest cannot turn arbitrary prose into Experiment Evidence.

Artifact bytes are protected through the existing ArtifactRegistry checksum audit. If the selected output file changes after review without an explicit manifest refresh and new review, execution is rejected.

## Persistence and rollback

Only explicit `execute()` writes canonical Evidence through `ClaimEvidenceRegistry`.

After writing, the bridge:

1. reloads each Evidence record and checks exact equality with the reviewed preview;
2. runs Claim/Evidence graph audit for structural errors affecting the new Evidence;
3. best-effort removes newly written files if execution or post-write validation fails.

This is in-process best-effort rollback, not a crash-safe database transaction.

## Scientific authority boundary

The bridge does not create `ClaimEvidenceLink` records.

In particular:

```text
ExperimentRun output exists
        !=
output supports a Claim
```

and:

```text
Run status = completed
        !=
scientifically correct / statistically significant / reproduced successfully
```

A diagnostic Artifact from a failed or partial Run may be preserved as Evidence material, but its existence does not imply a scientific conclusion.

## Deferred

Phase 5C does not implement:

- experiment scheduling or execution;
- parameter sweeps;
- result parsing or numerical comparison;
- statistical significance testing;
- reproducibility success scoring;
- automatic ClaimEvidenceLink creation or acceptance;
- automatic Claim approval/rejection;
- LLM or agent orchestration;
- manuscript generation.
