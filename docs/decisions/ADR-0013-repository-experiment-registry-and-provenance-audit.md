# ADR-0013: Repository Experiment Registry and Provenance Audit

- Status: Accepted
- Date: 2026-09-03

## Context

Phase 5A defined framework-neutral `Experiment` and `ExperimentRun` contracts. The system now needs deterministic repository persistence and cross-record integrity checks before any scheduler, runner, reproducibility workflow, or experiment-output-to-Evidence bridge is introduced.

The registry must preserve the project's repository-centric architecture and must not collapse operational execution facts into scientific interpretation.

## Decision

### 1. Repository JSON is canonical Experiment state

Persist Experiment state at:

```text
experiments/<experiment-id>/experiment.json
experiments/<experiment-id>/runs/<run-id>.json
```

External experiment trackers, databases, scheduler state, dashboards, or query indexes may be added later only as derived or explicitly governed representations.

### 2. Persistence and repository integrity remain separate operations

`save_experiment()` and `save_run()` persist already-valid object-level contracts without silently resolving or repairing cross-record references.

`audit()` is the explicit repository-level integrity operation.

This separation keeps persistence deterministic and prevents write APIs from becoming implicit workflow engines.

### 3. Run-to-Experiment binding is checked through the exact spec digest

Every Run stores the `experiment_spec_digest` defined in Phase 5A. Repository audit recomputes the digest of the current canonical Experiment and reports mismatch.

A mismatch is a provenance drift finding. It does not automatically invalidate or delete historical Run state.

### 4. All declared Artifact provenance is resolved through ArtifactRegistry

Audit verifies Experiment and Run Artifact references, including dirty-working-tree diff Artifacts and termination diagnostics.

Missing Artifacts are structural provenance errors. The registry does not synthesize replacements or rewrite references.

### 5. Run lineage is a repository graph and must remain acyclic

`rerun` and `reproduction` parent Runs must exist. Cross-record cycles are invalid and reported by audit.

The relation still represents execution intent only. An acyclic `reproduction` chain is not evidence that reproduction succeeded scientifically.

### 6. Malformed records must not prevent global audit

Invalid Experiment or Run files generate findings and are skipped for subsequent typed checks. The remainder of the repository is still audited.

### 7. Findings remain structural/operational

Phase 5B findings describe persistence, provenance, reference, digest, and lineage integrity only.

They do not encode:

- statistical significance;
- scientific correctness;
- hypothesis support;
- successful reproduction;
- Evidence eligibility;
- manuscript readiness.

## Consequences

### Positive

- Experiment provenance is Git-reviewable and portable.
- Runs remain bound to exact intended Experiment state.
- Dirty code and execution diagnostics remain auditable through Artifact references.
- Broken lineage or missing provenance becomes visible before higher-level research workflows consume Run state.
- Future schedulers and dashboards can be adapters rather than canonical databases.

### Costs

- Repository audit may require scanning multiple Experiment directories and resolving many Artifact manifests.
- Canonical Experiment edits can intentionally cause historical Run digest mismatches until versioning/migration policy is introduced.
- The current registry provides per-file atomic replacement, not database transactions or cross-process locking.

## Rejected alternatives

### Make an external experiment tracker canonical

Rejected because research-critical provenance would become dependent on an external service and harder to review through Git history.

### Rewrite old Runs when an Experiment changes

Rejected because it would destroy the exact specification binding that makes historical Runs reproducible and auditable.

### Treat reproduction lineage as a success flag

Rejected because execution intent and scientific reproduction assessment are distinct scientific states.

### Automatically create Evidence from completed Runs

Rejected because execution completion does not establish scientific meaning, quality, or claim support.

## Deferred

Later phases may add:

- reviewed Experiment-output-to-Evidence proposals;
- local/remote execution adapters;
- parameter sweep planning;
- crash-safe or concurrent registry mutation;
- Experiment version/migration policy;
- quantitative reproducibility comparison;
- scheduler or workflow integration.

None of those are part of Phase 5B.
