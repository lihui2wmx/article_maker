# ADR-0014: Reviewed ExperimentRun Artifact promotion to Evidence

**Status:** Accepted

## Context

Phase 5A defined `Experiment` and `ExperimentRun` provenance contracts. Phase 5B added repository persistence and read-only provenance audit. The system now needs a controlled way to move selected run artifacts into the Claim/Evidence scientific state without confusing execution provenance with scientific interpretation.

Experiment outputs and diagnostics are heterogeneous. A completed run does not establish correctness or significance, and a failed-run diagnostic can still be important research material. Automatically turning every output into Evidence, or automatically attaching it to Claims, would collapse provenance and interpretation into one uncontrolled transition.

## Decision

### 1. Promotion starts from explicit Run + Artifact selections

The bridge never scans all outputs and promotes them automatically. A caller must identify an Experiment, Run, Artifact, and optional locator.

The Artifact must belong to exactly one eligible Run provenance role: output or termination diagnostic.

### 2. Provenance role is derived mechanically

The bridge derives `output` or `diagnostic` only from the Run record. It does not accept a caller-supplied role and rejects ambiguous membership.

Output selections become `Evidence(kind=experiment_result)`. Diagnostic selections become `Evidence(kind=other)` so logs and failure diagnostics are not mislabeled as experimental results.

### 3. Evidence prose is mechanical

The generated Evidence description contains only source identity and locator information. Phase 5C does not accept or generate free-form scientific interpretation during promotion.

### 4. Exact source snapshots are review-bound

A plan records digests of:

- the canonical Experiment record;
- the canonical ExperimentRun record;
- the selected Artifact manifest;
- the complete generated Evidence preview.

Execution requires the exact reviewed plan digest.

### 5. Artifact filesystem drift is part of stale-source detection

The selected Artifact must pass ArtifactRegistry audit during planning and execution. Checksum/path/status drift therefore blocks promotion even when the Artifact manifest JSON itself did not change.

### 6. Preview regeneration prevents arbitrary Evidence injection

Execution regenerates the Evidence preview from current canonical source records and requires exact equality with the reviewed preview. Recomputing a digest over a manually altered Evidence object is not sufficient to make it eligible.

### 7. Canonical Evidence write is explicit and post-audited

Planning is read-only. Only explicit reviewed execution writes Evidence. Persistence is followed by exact reload equality and structural Claim/Evidence audit. New files are best-effort rolled back on in-process failure.

### 8. Scientific interpretation remains separate

Phase 5C does not create or approve ClaimEvidenceLink records, judge support/contradiction, assess statistical significance, determine reproduction success, or change Claim/Hypothesis status.

## Consequences

### Positive

- Experiment-derived Evidence has exact repository provenance.
- Human or workflow review sees the exact object before canonical write.
- Output-file drift after review cannot silently enter Evidence.
- Failed-run diagnostics can be preserved without being called experiment results.
- Agent-generated interpretation cannot be injected through this mechanical bridge.

### Costs

- Promotion requires an explicit selection and review step.
- A changed Run, Experiment, or Artifact requires a new plan and review.
- Evidence material remains orphaned until a separate ClaimEvidenceLink workflow relates it to a Claim.
- Best-effort filesystem rollback is not crash-safe transactional storage.

## Rejected alternatives

### Promote every completed-run output automatically

Rejected because output existence and run completion do not establish scientific relevance or validity.

### Allow caller-supplied free-form Evidence description

Rejected in this bridge because it would mix scientific interpretation into provenance promotion.

### Treat diagnostics as `experiment_result`

Rejected because logs and failure diagnostics are execution provenance, not necessarily experimental results.

### Automatically create `supports` or `contradicts` links

Rejected because those are governed scientific interpretations requiring a separate proposal/review transition.

### Trust Artifact manifest JSON without checking filesystem drift

Rejected because a source file can change after review while the manifest remains unchanged.

## Deferred

Future phases may add reviewed Claim-link proposal workflows, result extraction, statistical analysis, reproducibility comparison, and execution adapters. Those capabilities must preserve the provenance/interpretation separation established here.
