from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError as SchemaValidationError
from pydantic import ValidationError

from article_maker import (
    CodeProvenance,
    ExecutionEnvironment,
    Experiment,
    ExperimentRun,
    ExperimentRunStatus,
    ProposalAttribution,
    ProposalSource,
    RunLineage,
    RunLineageRelation,
    RunTermination,
    experiment_spec_digest,
)

SCHEMA = json.loads(
    (Path(__file__).parents[1] / "schemas" / "experiment.schema.json").read_text(
        encoding="utf-8"
    )
)


def attribution() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="experiment-agent")


def code(*, dirty: bool = False) -> CodeProvenance:
    return CodeProvenance(
        git_revision="0123456789abcdef",
        repository="lihui2wmx/article_maker",
        dirty=dirty,
        working_tree_diff_artifact_id="art-worktree-diff" if dirty else None,
        code_artifact_ids=["art-solver-code"],
    )


def environment() -> ExecutionEnvironment:
    return ExecutionEnvironment(
        runtime="python 3.11.9",
        operating_system="ubuntu-24.04",
        architecture="x86_64",
        container_image="ghcr.io/example/solver@sha256:deadbeef",
        environment_artifact_ids=["art-lockfile"],
        metadata={"blas": "openblas"},
    )


def experiment() -> Experiment:
    return Experiment(
        schema_version="1.0",
        experiment_id="exp-regularization-study",
        title="Regularization robustness study",
        objective="Measure nonlinear solver robustness under regularization.",
        proposed_by=attribution(),
        input_artifact_ids=["art-benchmark-dataset"],
        config_artifact_ids=["art-experiment-config"],
        parameters={"regularization": [0.0, 0.01, 0.1], "seed": 17},
        expected_code=code(),
        expected_environment=environment(),
        metadata={"campaign": "solver-robustness"},
    )


def completed_run() -> ExperimentRun:
    spec = experiment()
    return ExperimentRun(
        schema_version="1.0",
        run_id="exprun-regularization-001",
        experiment_id=spec.experiment_id,
        experiment_spec_digest=experiment_spec_digest(spec),
        status=ExperimentRunStatus.COMPLETED,
        started_at=datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 9, 3, 0, 5, tzinfo=timezone.utc),
        executed_by=attribution(),
        input_artifact_ids=["art-benchmark-dataset"],
        config_artifact_ids=["art-experiment-config"],
        resolved_parameters={"regularization": 0.01, "seed": 17},
        code=code(),
        environment=environment(),
        output_artifact_ids=["art-run-results"],
        metadata={"worker": "local"},
    )


def test_experiment_schema_is_valid_draft_202012() -> None:
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("model", [experiment(), completed_run()])
def test_valid_models_pass_framework_neutral_schema(model) -> None:
    Draft202012Validator(SCHEMA).validate(model.model_dump(mode="json"))


def test_experiment_spec_digest_is_deterministic_and_content_sensitive() -> None:
    first = experiment()
    payload = first.model_dump()
    second = Experiment(**payload)

    assert experiment_spec_digest(first) == experiment_spec_digest(second)
    assert len(experiment_spec_digest(first)) == 64

    payload["parameters"] = {"seed": 18, "regularization": [0.0, 0.01, 0.1]}
    changed = Experiment(**payload)
    assert experiment_spec_digest(first) != experiment_spec_digest(changed)


def test_dirty_code_requires_diff_artifact_and_clean_code_forbids_it() -> None:
    with pytest.raises(ValidationError):
        CodeProvenance(
            git_revision="0123456789abcdef",
            dirty=True,
            code_artifact_ids=[],
        )

    with pytest.raises(ValidationError):
        CodeProvenance(
            git_revision="0123456789abcdef",
            dirty=False,
            working_tree_diff_artifact_id="art-worktree-diff",
            code_artifact_ids=[],
        )

    schema_payload = code(dirty=True).model_dump(mode="json")
    schema_payload["working_tree_diff_artifact_id"] = None
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(SCHEMA["$defs"]["code_provenance"], registry=None).validate(schema_payload)


def test_run_lifecycle_separates_execution_state_from_scientific_quality() -> None:
    run = completed_run()
    assert run.status is ExperimentRunStatus.COMPLETED
    assert "quality" not in run.model_fields
    assert "significance" not in run.model_fields
    assert "supports_hypothesis" not in run.model_fields


def test_planned_running_and_terminal_timestamp_rules() -> None:
    base = completed_run().model_dump()

    planned = dict(base)
    planned.update(status="planned", started_at=None, finished_at=None, termination=None)
    ExperimentRun(**planned)

    running = dict(base)
    running.update(status="running", finished_at=None, termination=None)
    ExperimentRun(**running)

    bad_running = dict(running)
    bad_running["started_at"] = None
    with pytest.raises(ValidationError):
        ExperimentRun(**bad_running)

    failed = dict(base)
    failed.update(
        status="failed",
        termination=RunTermination(
            reason="solver diverged",
            stage="nonlinear-solve",
            diagnostic_artifact_ids=["art-run-log"],
        ),
    )
    ExperimentRun(**failed)

    bad_failed = dict(failed)
    bad_failed["termination"] = None
    with pytest.raises(ValidationError):
        ExperimentRun(**bad_failed)


def test_terminal_timestamp_order_and_timezone_are_validated() -> None:
    payload = completed_run().model_dump()
    payload["finished_at"] = datetime(2026, 9, 2, 23, 59, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        ExperimentRun(**payload)

    payload = completed_run().model_dump()
    payload["started_at"] = datetime(2026, 9, 3, 0, 0)
    with pytest.raises(ValidationError):
        ExperimentRun(**payload)


def test_partial_and_cancelled_runs_require_explicit_termination() -> None:
    base = completed_run().model_dump()
    for status in ("partial", "cancelled"):
        payload = dict(base)
        payload.update(
            status=status,
            termination=RunTermination(reason=f"{status} by operator"),
        )
        ExperimentRun(**payload)

        payload["termination"] = None
        with pytest.raises(ValidationError):
            ExperimentRun(**payload)


def test_rerun_and_reproduction_lineage_are_intent_not_success_claims() -> None:
    rerun = RunLineage(
        relation=RunLineageRelation.RERUN,
        parent_run_id="exprun-regularization-000",
    )
    reproduction = RunLineage(
        relation=RunLineageRelation.REPRODUCTION,
        parent_run_id="exprun-external-reproduction",
    )
    assert rerun.relation is RunLineageRelation.RERUN
    assert reproduction.relation is RunLineageRelation.REPRODUCTION

    payload = completed_run().model_dump()
    payload["lineage"] = {
        "relation": "rerun",
        "parent_run_id": payload["run_id"],
    }
    with pytest.raises(ValidationError):
        ExperimentRun(**payload)


def test_artifact_reference_lists_reject_duplicates() -> None:
    payload = experiment().model_dump()
    payload["input_artifact_ids"] = ["art-benchmark-dataset", "art-benchmark-dataset"]
    with pytest.raises(ValidationError):
        Experiment(**payload)

    payload = completed_run().model_dump()
    payload["output_artifact_ids"] = ["art-run-results", "art-run-results"]
    with pytest.raises(ValidationError):
        ExperimentRun(**payload)


def test_parameters_environment_and_metadata_are_json_only() -> None:
    payload = experiment().model_dump()
    payload["parameters"] = {"opaque": object()}
    with pytest.raises(ValidationError):
        Experiment(**payload)

    payload = completed_run().model_dump()
    payload["environment"] = environment().model_dump()
    payload["environment"]["metadata"] = {"opaque": object()}
    with pytest.raises(ValidationError):
        ExperimentRun(**payload)


def test_invalid_ids_revisions_and_spec_digest_are_rejected() -> None:
    payload = experiment().model_dump()
    payload["experiment_id"] = "experiment-1"
    with pytest.raises(ValidationError):
        Experiment(**payload)

    payload = completed_run().model_dump()
    payload["run_id"] = "run-1"
    with pytest.raises(ValidationError):
        ExperimentRun(**payload)

    payload = completed_run().model_dump()
    payload["experiment_spec_digest"] = "ABC"
    with pytest.raises(ValidationError):
        ExperimentRun(**payload)

    with pytest.raises(ValidationError):
        CodeProvenance(git_revision="main", dirty=False)
