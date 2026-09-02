# Experiment Provenance Contracts

Phase 5A introduces canonical, framework-neutral contracts for experiment intent and observed execution provenance.

## Separation of concerns

`Experiment` and `ExperimentRun` deliberately represent different facts.

- `Experiment` describes an intended protocol/specification: objective, inputs, configuration, parameter space, expected code revision, and expected environment.
- `ExperimentRun` records one observed execution: the exact experiment-spec digest, actual inputs/configuration, resolved parameters, observed code/environment, execution timestamps/status, outputs, termination details, and optional rerun/reproduction lineage.

A completed run is only an execution fact. It does not mean the result is scientifically correct, statistically significant, reproducible, supportive of a hypothesis, or suitable for a manuscript.

## Stable identities

- Experiment IDs use `exp-*`.
- ExperimentRun IDs use `exprun-*`.

IDs are stable repository identities and are independent from filenames, scheduler job IDs, process IDs, timestamps, or external compute platforms.

## Experiment specification digest

`experiment_spec_digest(experiment)` computes SHA-256 over canonical JSON serialization of the entire validated `Experiment` object.

Each `ExperimentRun` stores this digest in `experiment_spec_digest` so later repository-level audit can determine exactly which intended specification the run claims to execute.

Phase 5A defines the digest and field only. Cross-file resolution and stale-spec auditing are deferred to Phase 5B.

## Artifact provenance

Both specifications and runs use canonical `art-*` references.

`Experiment` may reference:

- `input_artifact_ids` for datasets or other scientific inputs;
- `config_artifact_ids` for explicit configuration files;
- code artifacts through `expected_code.code_artifact_ids`;
- environment artifacts such as lockfiles through `expected_environment.environment_artifact_ids`.

`ExperimentRun` records the actual corresponding Artifact references and adds `output_artifact_ids` for persisted run products.

Object-level contracts validate ID syntax and duplicates. Repository-level existence and semantic consistency are deferred to Phase 5B.

## Code provenance

`CodeProvenance` requires a lowercase hexadecimal Git revision.

A dirty working tree is allowed only when the exact diff is itself preserved as an Artifact:

```text
dirty = true
    -> working_tree_diff_artifact_id is required
```

A clean code state must not declare a working-tree diff Artifact.

This prevents a run from claiming reproducible code provenance while silently depending on uncommitted changes.

## Execution environment

`ExecutionEnvironment` records reproducibility-relevant facts such as:

- runtime;
- operating system;
- architecture;
- container image identifier/digest when available;
- environment Artifact references such as lockfiles or environment manifests;
- JSON-compatible metadata for lower-criticality details.

The contract does not require containers and does not privilege a specific execution framework.

## Parameter/config representation

`Experiment.parameters` and `ExperimentRun.resolved_parameters` are JSON-only mappings.

The Experiment mapping describes intended configuration or parameter space. The run mapping records the actual resolved parameter values used by one execution.

No Python-specific objects, callbacks, opaque class instances, or framework-native configuration objects are allowed in canonical parameter state.

## Run lifecycle

Execution status is intentionally operational:

- `planned`
- `running`
- `completed`
- `failed`
- `cancelled`
- `partial`

Lifecycle invariants:

- `planned`: no start/finish timestamp and no termination details;
- `running`: requires `started_at`, forbids `finished_at` and termination details;
- `completed`: requires start and finish timestamps and forbids termination details;
- `failed`, `cancelled`, `partial`: require start/finish timestamps and explicit `RunTermination` details;
- `finished_at` must not precede `started_at`;
- timestamps must be timezone-aware.

`RunTermination` may preserve the reason, execution stage, and diagnostic Artifacts.

## Rerun and reproduction lineage

`RunLineage` supports:

- `rerun`: another execution intentionally derived from an earlier run within an experiment workflow;
- `reproduction`: an execution intended to reproduce an earlier run.

The relation records intent only. It does **not** assert that a reproduction succeeded scientifically or numerically.

A run cannot name itself as its lineage parent. Parent existence, acyclicity across repository records, and compatibility with Experiment identity/specification are deferred to Phase 5B.

## Scientific authority boundary

Phase 5A does not define or infer:

- result quality;
- statistical significance;
- hypothesis support;
- Claim approval;
- Evidence creation;
- reproducibility success;
- publication readiness.

Experiment outputs remain repository Artifacts until a later explicit, reviewable workflow proposes scientific Evidence or other governed state.

## Framework-neutral contract

The language-independent contract is `schemas/experiment.schema.json` using JSON Schema Draft 2020-12.

`src/article_maker/experiment.py` is the initial Python/Pydantic implementation. Repository JSON remains the canonical scientific state; scheduler databases, HPC metadata stores, CI job records, and experiment-tracking services may later be derived/integrated representations but must not silently replace the repository source of truth.
