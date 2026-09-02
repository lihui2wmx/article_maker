# ADR-0012: Experiment/run provenance and lifecycle semantics

- **Status:** Accepted for Phase 5A
- **Date:** 2026-09-03

## Context

`article_maker` needs experiment records that remain reproducible and auditable independently from any scheduler, cloud/HPC runner, experiment-tracking vendor, or AI agent framework.

The system must also prevent execution facts from being confused with scientific conclusions. A process exiting successfully is not evidence that a result is correct, significant, reproducible, or supportive of a Claim.

Several choices materially constrain later experiment execution, registry, Evidence promotion, and reproducibility auditing:

1. whether experiment intent and individual executions share one object;
2. what constitutes stable identity;
3. how a run binds to the intended specification it claims to execute;
4. how uncommitted code is represented;
5. how failure/partial execution is recorded;
6. what rerun/reproduction lineage means;
7. whether scheduler/tracker state can become canonical.

## Decision

### 1. Separate Experiment from ExperimentRun

`Experiment` is the intended protocol/specification. `ExperimentRun` is one observed execution.

The two must remain separate canonical objects because one Experiment can have many runs, and runs may differ in observed environment, resolved parameters, outputs, termination state, or lineage.

### 2. Use repository-stable internal IDs

- Experiment: `exp-*`
- ExperimentRun: `exprun-*`

These identifiers are independent from scheduler IDs, process IDs, timestamps, filenames, cloud job IDs, or third-party tracking IDs.

### 3. Bind each run to an exact Experiment specification digest

Every ExperimentRun contains `experiment_spec_digest`, computed from canonical JSON serialization of the entire validated Experiment object.

Phase 5A does not resolve that digest against repository files; Phase 5B will own cross-record validation.

### 4. Preserve dirty code explicitly

`CodeProvenance` requires a Git revision.

If `dirty=true`, a `working_tree_diff_artifact_id` is mandatory. If `dirty=false`, a working-tree diff Artifact is forbidden.

This allows dirty executions when necessary without treating them as if the Git revision alone reproduced the exact code state.

### 5. Keep environment representation framework-neutral

`ExecutionEnvironment` records runtime, optional OS/architecture/container identity, environment Artifact references, and JSON metadata.

Containers are optional. No Docker, Conda, Nix, Slurm, Kubernetes, MLflow, Weights & Biases, or other framework becomes part of the core contract.

### 6. Treat parameters/configuration as JSON canonical state

Experiment intended parameters and run resolved parameters are JSON-only mappings. Opaque framework objects are not canonical configuration.

### 7. Make run lifecycle operational only

Run status is limited to:

- planned;
- running;
- completed;
- failed;
- cancelled;
- partial.

Lifecycle states control timestamp and termination-shape invariants only. They encode no scientific quality judgment.

Terminal non-completed states require explicit termination details. Completed runs forbid termination details.

### 8. Treat rerun/reproduction lineage as intent, not success

`RunLineage` may mark a run as a `rerun` or `reproduction` of one parent run.

This records why the execution exists. It does not assert numerical agreement or scientific reproducibility. Those judgments belong to later reproducibility analysis and, where scientifically substantive, human review.

### 9. Keep repository records canonical

External experiment trackers, scheduler databases, CI systems, HPC job metadata, or derived indexes may be integrated later, but none becomes the only canonical copy of research-critical experiment state without a new architecture decision.

## Consequences

### Positive

- repeated executions do not overwrite experiment intent;
- exact intended-spec binding is auditable;
- dirty-code runs remain representable without hiding uncommitted changes;
- failure and partial runs remain useful scientific provenance instead of disappearing;
- scheduler/runtime choices stay replaceable;
- later Experiment-to-Evidence promotion can operate over stable provenance;
- completed execution cannot be mistaken for approved scientific evidence.

### Costs

- Experiment and ExperimentRun duplicate some intended/observed fields by design;
- repository-level audit is required to compare run state against the referenced Experiment and Artifacts;
- dirty execution requires preserving a diff Artifact;
- reproducibility success requires a later explicit analysis layer rather than a boolean in RunLineage.

## Deferred

Phase 5A deliberately does not define:

- canonical filesystem registry layout or cross-record Experiment audit;
- scheduler or executor APIs;
- remote/cloud/HPC execution;
- concurrency/locking for run persistence;
- automatic parameter sweep expansion;
- statistical analysis;
- reproducibility scoring;
- automatic Evidence/Claim creation from outputs;
- LLM or multi-agent orchestration;
- manuscript integration.
