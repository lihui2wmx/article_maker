from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from article_maker import (
    ArtifactKind,
    ArtifactRegistry,
    CodeProvenance,
    ExecutionEnvironment,
    Experiment,
    ExperimentNotFoundError,
    ExperimentRegistry,
    ExperimentRegistryError,
    ExperimentRun,
    ExperimentRunStatus,
    ProducerType,
    ProposalAttribution,
    ProposalSource,
    RunLineage,
    RunLineageRelation,
    RunTermination,
    experiment_spec_digest,
)


def attribution() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="experiment-agent")


def register_artifact(root: Path, artifact_id: str) -> None:
    path = root / "data" / f"{artifact_id}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(artifact_id, encoding="utf-8")
    ArtifactRegistry(root).register(
        str(path.relative_to(root)),
        kind=ArtifactKind.OTHER,
        producer=ProducerType.HUMAN,
        artifact_id=artifact_id,
    )


def register_standard_artifacts(root: Path) -> None:
    for artifact_id in (
        "art-input-data",
        "art-config-file",
        "art-code-snapshot",
        "art-environment-lock",
        "art-run-output",
        "art-run-log",
    ):
        register_artifact(root, artifact_id)


def experiment() -> Experiment:
    return Experiment(
        schema_version="1.0",
        experiment_id="exp-registry-study",
        title="Registry provenance study",
        objective="Exercise repository-level experiment provenance checks.",
        proposed_by=attribution(),
        input_artifact_ids=["art-input-data"],
        config_artifact_ids=["art-config-file"],
        parameters={"seed": 17, "alpha": 0.1},
        expected_code=CodeProvenance(
            git_revision="0123456789abcdef",
            repository="lihui2wmx/article_maker",
            code_artifact_ids=["art-code-snapshot"],
        ),
        expected_environment=ExecutionEnvironment(
            runtime="python 3.11",
            operating_system="ubuntu-24.04",
            environment_artifact_ids=["art-environment-lock"],
        ),
    )


def completed_run(*, run_id: str = "exprun-registry-001") -> ExperimentRun:
    spec = experiment()
    return ExperimentRun(
        schema_version="1.0",
        run_id=run_id,
        experiment_id=spec.experiment_id,
        experiment_spec_digest=experiment_spec_digest(spec),
        status=ExperimentRunStatus.COMPLETED,
        started_at=datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 9, 3, 0, 5, tzinfo=timezone.utc),
        executed_by=attribution(),
        input_artifact_ids=["art-input-data"],
        config_artifact_ids=["art-config-file"],
        resolved_parameters={"seed": 17, "alpha": 0.1},
        code=CodeProvenance(
            git_revision="0123456789abcdef",
            repository="lihui2wmx/article_maker",
            code_artifact_ids=["art-code-snapshot"],
        ),
        environment=ExecutionEnvironment(
            runtime="python 3.11",
            operating_system="ubuntu-24.04",
            environment_artifact_ids=["art-environment-lock"],
        ),
        output_artifact_ids=["art-run-output"],
    )


def finding_codes(registry: ExperimentRegistry) -> set[str]:
    return {finding.code for finding in registry.audit()}


def test_clean_registry_persists_canonical_layout_and_audits_cleanly(tmp_path: Path) -> None:
    register_standard_artifacts(tmp_path)
    registry = ExperimentRegistry(tmp_path)
    spec = experiment()
    run = completed_run()

    registry.save_experiment(spec)
    registry.save_run(run)

    experiment_path = tmp_path / "experiments" / spec.experiment_id / "experiment.json"
    run_path = tmp_path / "experiments" / spec.experiment_id / "runs" / f"{run.run_id}.json"
    assert experiment_path.is_file()
    assert run_path.is_file()
    assert experiment_path.read_text(encoding="utf-8").endswith("\n")
    assert registry.load_experiment(spec.experiment_id) == spec
    assert registry.load_run(spec.experiment_id, run.run_id) == run
    assert registry.list_experiments() == [spec]
    assert registry.list_runs() == [run]
    assert registry.audit() == []


def test_missing_experiment_and_spec_digest_mismatch_are_audited(tmp_path: Path) -> None:
    register_standard_artifacts(tmp_path)
    registry = ExperimentRegistry(tmp_path)

    registry.save_run(completed_run())
    assert "missing-experiment" in finding_codes(registry)

    registry.save_experiment(experiment())
    payload = completed_run(run_id="exprun-registry-002").model_dump()
    payload["experiment_spec_digest"] = "0" * 64
    registry.save_run(ExperimentRun(**payload))
    assert "experiment-spec-digest-mismatch" in finding_codes(registry)


def test_experiment_and_run_artifact_references_are_audited(tmp_path: Path) -> None:
    registry = ExperimentRegistry(tmp_path)
    registry.save_experiment(experiment())

    payload = completed_run().model_dump()
    payload.update(
        status="failed",
        termination=RunTermination(
            reason="solver failed",
            diagnostic_artifact_ids=["art-run-log"],
        ),
    )
    registry.save_run(ExperimentRun(**payload))

    findings = registry.audit()
    assert "missing-artifact" in {finding.code for finding in findings}
    messages = "\n".join(finding.message for finding in findings)
    assert "experiment input Artifact" in messages
    assert "run output Artifact" in messages
    assert "run diagnostic Artifact" in messages


def test_dirty_code_diff_artifacts_are_audited(tmp_path: Path) -> None:
    register_standard_artifacts(tmp_path)
    registry = ExperimentRegistry(tmp_path)

    spec_payload = experiment().model_dump()
    spec_payload["expected_code"] = CodeProvenance(
        git_revision="0123456789abcdef",
        dirty=True,
        working_tree_diff_artifact_id="art-missing-diff",
        code_artifact_ids=["art-code-snapshot"],
    )
    dirty_spec = Experiment(**spec_payload)
    registry.save_experiment(dirty_spec)

    run_payload = completed_run().model_dump()
    run_payload["experiment_spec_digest"] = experiment_spec_digest(dirty_spec)
    run_payload["code"] = CodeProvenance(
        git_revision="0123456789abcdef",
        dirty=True,
        working_tree_diff_artifact_id="art-missing-run-diff",
        code_artifact_ids=["art-code-snapshot"],
    )
    registry.save_run(ExperimentRun(**run_payload))

    messages = "\n".join(finding.message for finding in registry.audit())
    assert "expected dirty-code diff Artifact" in messages
    assert "run dirty-code diff Artifact" in messages


def test_missing_lineage_parent_and_lineage_cycle_are_audited(tmp_path: Path) -> None:
    register_standard_artifacts(tmp_path)
    registry = ExperimentRegistry(tmp_path)
    registry.save_experiment(experiment())

    missing_parent_payload = completed_run(run_id="exprun-registry-missing-parent").model_dump()
    missing_parent_payload["lineage"] = RunLineage(
        relation=RunLineageRelation.RERUN,
        parent_run_id="exprun-registry-does-not-exist",
    )
    registry.save_run(ExperimentRun(**missing_parent_payload))
    assert "missing-lineage-parent" in finding_codes(registry)

    first_payload = completed_run(run_id="exprun-registry-cycle-a").model_dump()
    first_payload["lineage"] = {
        "relation": "rerun",
        "parent_run_id": "exprun-registry-cycle-b",
    }
    second_payload = completed_run(run_id="exprun-registry-cycle-b").model_dump()
    second_payload["lineage"] = {
        "relation": "reproduction",
        "parent_run_id": "exprun-registry-cycle-a",
    }
    registry.save_run(ExperimentRun(**first_payload))
    registry.save_run(ExperimentRun(**second_payload))
    assert "run-lineage-cycle" in finding_codes(registry)


def test_directory_filename_and_duplicate_ids_are_audited(tmp_path: Path) -> None:
    register_standard_artifacts(tmp_path)
    registry = ExperimentRegistry(tmp_path)
    spec = experiment()
    run = completed_run()

    wrong_dir = tmp_path / "experiments" / "exp-wrong-directory"
    wrong_dir.mkdir(parents=True)
    (wrong_dir / "experiment.json").write_text(
        json.dumps(spec.model_dump(mode="json")), encoding="utf-8"
    )
    runs_dir = wrong_dir / "runs"
    runs_dir.mkdir()
    (runs_dir / "exprun-wrong-filename.json").write_text(
        json.dumps(run.model_dump(mode="json")), encoding="utf-8"
    )

    correct_dir = tmp_path / "experiments" / spec.experiment_id
    correct_runs = correct_dir / "runs"
    correct_runs.mkdir(parents=True)
    (correct_dir / "experiment.json").write_text(
        json.dumps(spec.model_dump(mode="json")), encoding="utf-8"
    )
    (correct_runs / f"{run.run_id}.json").write_text(
        json.dumps(run.model_dump(mode="json")), encoding="utf-8"
    )

    codes = finding_codes(registry)
    assert "experiment-directory-id-mismatch" in codes
    assert "duplicate-experiment-id" in codes
    assert "run-filename-id-mismatch" in codes
    assert "run-experiment-directory-mismatch" in codes
    assert "duplicate-run-id" in codes


def test_malformed_records_do_not_abort_audit(tmp_path: Path) -> None:
    register_standard_artifacts(tmp_path)
    registry = ExperimentRegistry(tmp_path)
    registry.save_experiment(experiment())
    registry.save_run(completed_run())

    broken_experiment_dir = tmp_path / "experiments" / "exp-broken-record"
    broken_experiment_dir.mkdir(parents=True)
    (broken_experiment_dir / "experiment.json").write_text("{broken", encoding="utf-8")
    broken_runs = broken_experiment_dir / "runs"
    broken_runs.mkdir()
    (broken_runs / "exprun-broken-record.json").write_text("[]", encoding="utf-8")

    codes = finding_codes(registry)
    assert "invalid-experiment-record" in codes
    assert "invalid-run-record" in codes


def test_registry_path_escape_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ExperimentRegistryError):
        ExperimentRegistry(tmp_path, experiments_path="../outside")

    with pytest.raises(ExperimentRegistryError):
        ExperimentRegistry(tmp_path, experiments_path=str((tmp_path / "outside").resolve()))


def test_missing_loads_raise_typed_error(tmp_path: Path) -> None:
    registry = ExperimentRegistry(tmp_path)
    with pytest.raises(ExperimentNotFoundError):
        registry.load_experiment("exp-missing-record")
    with pytest.raises(ExperimentNotFoundError):
        registry.load_run("exp-missing-record", "exprun-missing-record")
