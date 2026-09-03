# Experiment Registry and Provenance Audit

Phase 5B persists `Experiment` and `ExperimentRun` records as repository-native canonical state and audits reproducibility/provenance integrity without executing jobs or interpreting scientific results.

## Canonical layout

```text
experiments/
└── <experiment-id>/
    ├── experiment.json
    └── runs/
        └── <run-id>.json
```

`ExperimentRegistry` is filesystem-backed. The repository remains the source of truth; any database, scheduler state, workflow engine, or external experiment tracker added later must be reconstructible from repository state or explicitly governed by a later architecture decision.

## Persistence API

```python
registry = ExperimentRegistry(repository_root)
registry.save_experiment(experiment)
registry.save_run(run)

experiment = registry.load_experiment("exp-study")
run = registry.load_run("exp-study", "exprun-study-001")
```

Writes use deterministic UTF-8 JSON with sorted keys and trailing newline, written through a same-directory temporary file followed by `os.replace`.

`save_experiment()` and `save_run()` persist already-valid object-level contracts. They do not resolve cross-record references before writing. Repository-level integrity is assessed explicitly with `audit()`.

## Audit boundary

`audit()` is read-only and checks:

- Experiment directory identity;
- duplicate Experiment IDs;
- malformed Experiment records;
- Experiment input/config/code/environment Artifact existence;
- ExperimentRun filename identity;
- ExperimentRun storage directory vs `experiment_id`;
- duplicate Run IDs across the repository;
- malformed Run records;
- Run -> Experiment existence;
- Run `experiment_spec_digest` against the current canonical Experiment;
- Run input/config/code/environment/output Artifact existence;
- dirty-working-tree diff Artifact existence;
- failure/partial/cancelled diagnostic Artifact existence;
- rerun/reproduction parent Run existence;
- Run lineage cycles.

Malformed records produce findings and do not abort the rest of the audit.

## Spec digest drift

Each `ExperimentRun` records the exact `experiment_spec_digest` it was executed against. If the canonical `Experiment` later changes, audit reports:

```text
experiment-spec-digest-mismatch
```

This is a reproducibility/provenance finding. It does not by itself mean the Run is scientifically invalid. The historical Run remains an observation bound to an older Experiment specification.

## Artifact provenance

The audit resolves all repository Artifact references used by Experiment and Run state, including:

- experiment inputs;
- experiment config;
- intended code snapshots;
- intended environment/lock artifacts;
- dirty-code diff artifacts;
- run inputs and configs;
- observed code and environment artifacts;
- outputs;
- termination diagnostics.

Artifact existence is checked through the Phase 1 `ArtifactRegistry`. Missing references are never silently repaired.

## Run lineage

A Run may declare one parent relation:

- `rerun`;
- `reproduction`.

Phase 5B checks that the parent Run exists and that the repository lineage graph is acyclic.

Lineage means execution intent only. A valid reproduction lineage does **not** assert that numerical, statistical, or scientific reproduction succeeded.

## Finding semantics

Current Phase 5B findings are structural/operational errors. They do not encode scientific quality.

Representative finding codes include:

- `invalid-experiment-record`;
- `experiment-directory-id-mismatch`;
- `duplicate-experiment-id`;
- `invalid-run-record`;
- `run-filename-id-mismatch`;
- `run-experiment-directory-mismatch`;
- `duplicate-run-id`;
- `missing-experiment`;
- `experiment-spec-digest-mismatch`;
- `missing-artifact`;
- `missing-lineage-parent`;
- `run-lineage-cycle`.

## Non-goals

Phase 5B does not:

- schedule or execute experiments;
- launch local, cloud, container, or HPC jobs;
- expand parameter sweeps;
- score reproducibility success;
- compare numerical results;
- perform statistical interpretation;
- promote outputs to Evidence;
- create ClaimEvidenceLink records;
- approve or reject Claims;
- invoke an LLM or agent runtime;
- generate manuscript content.

A later reviewed bridge may convert eligible experiment outputs into proposed Evidence, but that is deliberately separate from provenance recording and execution status.
