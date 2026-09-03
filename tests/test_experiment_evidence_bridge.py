from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from article_maker import (
    ArtifactKind,
    ArtifactRegistry,
    ClaimEvidenceNotFoundError,
    ClaimEvidenceRegistry,
    CodeProvenance,
    EvidenceKind,
    ExecutionEnvironment,
    Experiment,
    ExperimentEvidenceApprovalError,
    ExperimentEvidenceBridge,
    ExperimentEvidenceConflictError,
    ExperimentEvidenceEligibilityError,
    ExperimentEvidencePlan,
    ExperimentEvidencePlanError,
    ExperimentEvidenceRole,
    ExperimentEvidenceSelection,
    ExperimentEvidenceStaleError,
    ExperimentRegistry,
    ExperimentRun,
    ExperimentRunStatus,
    PlannedExperimentEvidence,
    ProducerType,
    ProposalAttribution,
    ProposalSource,
    RunTermination,
    experiment_evidence_plan_digest,
    experiment_spec_digest,
)


def attribution() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="experiment-agent")


def register_artifact(root: Path, artifact_id: str, *, content: str | None = None) -> Path:
    path = root / "data" / f"{artifact_id}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content or artifact_id, encoding="utf-8")
    ArtifactRegistry(root).register(
        str(path.relative_to(root)),
        kind=ArtifactKind.OTHER,
        producer=ProducerType.HUMAN,
        artifact_id=artifact_id,
    )
    return path


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
        experiment_id="exp-evidence-study",
        title="Experiment Evidence bridge study",
        objective="Exercise reviewed promotion of explicit run provenance.",
        proposed_by=attribution(),
        input_artifact_ids=["art-input-data"],
        config_artifact_ids=["art-config-file"],
        parameters={"seed": 17},
        expected_code=CodeProvenance(
            git_revision="0123456789abcdef",
            code_artifact_ids=["art-code-snapshot"],
        ),
        expected_environment=ExecutionEnvironment(
            runtime="python 3.11",
            environment_artifact_ids=["art-environment-lock"],
        ),
    )


def completed_run() -> ExperimentRun:
    spec = experiment()
    return ExperimentRun(
        schema_version="1.0",
        run_id="exprun-evidence-001",
        experiment_id=spec.experiment_id,
        experiment_spec_digest=experiment_spec_digest(spec),
        status=ExperimentRunStatus.COMPLETED,
        started_at=datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 9, 3, 0, 5, tzinfo=timezone.utc),
        executed_by=attribution(),
        input_artifact_ids=["art-input-data"],
        config_artifact_ids=["art-config-file"],
        resolved_parameters={"seed": 17},
        code=CodeProvenance(
            git_revision="0123456789abcdef",
            code_artifact_ids=["art-code-snapshot"],
        ),
        environment=ExecutionEnvironment(
            runtime="python 3.11",
            environment_artifact_ids=["art-environment-lock"],
        ),
        output_artifact_ids=["art-run-output"],
    )


def failed_run(*, ambiguous: bool = False) -> ExperimentRun:
    spec = experiment()
    diagnostics = ["art-run-output"] if ambiguous else ["art-run-log"]
    return ExperimentRun(
        schema_version="1.0",
        run_id="exprun-evidence-failed",
        experiment_id=spec.experiment_id,
        experiment_spec_digest=experiment_spec_digest(spec),
        status=ExperimentRunStatus.FAILED,
        started_at=datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 9, 3, 0, 2, tzinfo=timezone.utc),
        executed_by=attribution(),
        input_artifact_ids=["art-input-data"],
        config_artifact_ids=["art-config-file"],
        resolved_parameters={"seed": 17},
        code=CodeProvenance(
            git_revision="0123456789abcdef",
            code_artifact_ids=["art-code-snapshot"],
        ),
        environment=ExecutionEnvironment(
            runtime="python 3.11",
            environment_artifact_ids=["art-environment-lock"],
        ),
        output_artifact_ids=["art-run-output"],
        termination=RunTermination(
            reason="solver diverged",
            diagnostic_artifact_ids=diagnostics,
        ),
    )


def setup_repository(root: Path, run: ExperimentRun | None = None) -> ExperimentEvidenceBridge:
    register_standard_artifacts(root)
    registry = ExperimentRegistry(root)
    registry.save_experiment(experiment())
    registry.save_run(run or completed_run())
    return ExperimentEvidenceBridge(root)


def output_selection(*, locator: str | None = "table-1/row-2") -> ExperimentEvidenceSelection:
    return ExperimentEvidenceSelection(
        experiment_id="exp-evidence-study",
        run_id="exprun-evidence-001",
        artifact_id="art-run-output",
        locator=locator,
    )


def test_output_plan_is_deterministic_dry_run_with_exact_provenance(tmp_path: Path) -> None:
    bridge = setup_repository(tmp_path)

    first = bridge.plan([output_selection()])
    second = bridge.plan([output_selection()])

    assert experiment_evidence_plan_digest(first) == experiment_evidence_plan_digest(second)
    assert len(first.entries) == 1
    entry = first.entries[0]
    assert entry.role is ExperimentEvidenceRole.OUTPUT
    assert entry.evidence.kind is EvidenceKind.EXPERIMENT_RESULT
    assert entry.evidence.sources[0].artifact_id == "art-run-output"
    assert entry.evidence.sources[0].locator == "table-1/row-2"
    assert entry.evidence.description == (
        "ExperimentRun exprun-evidence-001 output Artifact art-run-output at table-1/row-2"
    )
    metadata = entry.evidence.metadata["experiment_bridge"]
    assert metadata["experiment_id"] == "exp-evidence-study"
    assert metadata["run_id"] == "exprun-evidence-001"
    assert metadata["run_status"] == "completed"
    assert metadata["artifact_role"] == "output"
    assert metadata["experiment_spec_digest"] == completed_run().experiment_spec_digest

    evidence_path = tmp_path / "evidence" / f"{entry.evidence.evidence_id}.json"
    assert not evidence_path.exists()


def test_failed_run_diagnostic_is_other_evidence_not_experiment_result(tmp_path: Path) -> None:
    bridge = setup_repository(tmp_path, failed_run())
    plan = bridge.plan(
        [
            ExperimentEvidenceSelection(
                experiment_id="exp-evidence-study",
                run_id="exprun-evidence-failed",
                artifact_id="art-run-log",
                locator="stderr/line-42",
            )
        ]
    )

    entry = plan.entries[0]
    assert entry.role is ExperimentEvidenceRole.DIAGNOSTIC
    assert entry.evidence.kind is EvidenceKind.OTHER
    assert entry.evidence.metadata["experiment_bridge"]["run_status"] == "failed"
    assert entry.evidence.metadata["experiment_bridge"]["artifact_role"] == "diagnostic"


def test_selection_must_belong_to_run_and_ambiguous_roles_are_rejected(tmp_path: Path) -> None:
    bridge = setup_repository(tmp_path)
    register_artifact(tmp_path, "art-unrelated")

    with pytest.raises(ExperimentEvidenceEligibilityError):
        bridge.plan(
            [
                ExperimentEvidenceSelection(
                    experiment_id="exp-evidence-study",
                    run_id="exprun-evidence-001",
                    artifact_id="art-unrelated",
                )
            ]
        )

    ExperimentRegistry(tmp_path).save_run(failed_run(ambiguous=True))
    with pytest.raises(ExperimentEvidenceEligibilityError):
        bridge.plan(
            [
                ExperimentEvidenceSelection(
                    experiment_id="exp-evidence-study",
                    run_id="exprun-evidence-failed",
                    artifact_id="art-run-output",
                )
            ]
        )


def test_duplicate_empty_and_blank_locator_selections_are_rejected(tmp_path: Path) -> None:
    bridge = setup_repository(tmp_path)

    with pytest.raises(ExperimentEvidencePlanError):
        bridge.plan([])
    with pytest.raises(ExperimentEvidencePlanError):
        bridge.plan([output_selection(locator="   ")])
    with pytest.raises(ExperimentEvidencePlanError):
        bridge.plan([output_selection(), output_selection()])


def test_plan_rejects_run_bound_to_stale_experiment_spec(tmp_path: Path) -> None:
    bridge = setup_repository(tmp_path)
    registry = ExperimentRegistry(tmp_path)
    payload = experiment().model_dump()
    payload["parameters"] = {"seed": 18}
    registry.save_experiment(Experiment(**payload))

    with pytest.raises(ExperimentEvidenceEligibilityError):
        bridge.plan([output_selection()])


def test_execute_requires_exact_reviewed_digest(tmp_path: Path) -> None:
    bridge = setup_repository(tmp_path)
    plan = bridge.plan([output_selection()])

    with pytest.raises(ExperimentEvidenceApprovalError):
        bridge.execute(plan, reviewed_digest="0" * 64)

    with pytest.raises(ClaimEvidenceNotFoundError):
        ClaimEvidenceRegistry(tmp_path).load_evidence(plan.entries[0].evidence.evidence_id)


def test_execute_rejects_run_change_after_review(tmp_path: Path) -> None:
    bridge = setup_repository(tmp_path)
    plan = bridge.plan([output_selection()])

    payload = completed_run().model_dump()
    payload["metadata"] = {"worker": "different-host"}
    ExperimentRegistry(tmp_path).save_run(ExperimentRun(**payload))

    with pytest.raises(ExperimentEvidenceStaleError):
        bridge.execute(plan, reviewed_digest=experiment_evidence_plan_digest(plan))


def test_execute_rejects_artifact_byte_drift_after_review(tmp_path: Path) -> None:
    bridge = setup_repository(tmp_path)
    plan = bridge.plan([output_selection()])

    output_path = tmp_path / "data" / "art-run-output.txt"
    output_path.write_text("changed after review", encoding="utf-8")

    with pytest.raises(ExperimentEvidenceEligibilityError):
        bridge.execute(plan, reviewed_digest=experiment_evidence_plan_digest(plan))


def test_modified_preview_is_rejected_even_with_recomputed_digest(tmp_path: Path) -> None:
    bridge = setup_repository(tmp_path)
    plan = bridge.plan([output_selection()])
    entry = plan.entries[0]
    evidence_payload = entry.evidence.model_dump()
    evidence_payload["description"] = "This output proves the hypothesis."
    modified_evidence = type(entry.evidence)(**evidence_payload)
    modified_entry = PlannedExperimentEvidence(
        experiment_id=entry.experiment_id,
        run_id=entry.run_id,
        artifact_id=entry.artifact_id,
        locator=entry.locator,
        role=entry.role,
        experiment_digest=entry.experiment_digest,
        run_digest=entry.run_digest,
        artifact_manifest_digest=entry.artifact_manifest_digest,
        evidence=modified_evidence,
    )
    modified_plan = ExperimentEvidencePlan(entries=(modified_entry,))

    with pytest.raises(ExperimentEvidencePlanError):
        bridge.execute(
            modified_plan,
            reviewed_digest=experiment_evidence_plan_digest(modified_plan),
        )


def test_successful_execute_persists_exact_reviewed_evidence(tmp_path: Path) -> None:
    bridge = setup_repository(tmp_path)
    plan = bridge.plan([output_selection()])
    digest = experiment_evidence_plan_digest(plan)

    result = bridge.execute(plan, reviewed_digest=digest)

    assert result.plan_digest == digest
    assert result.evidence_ids == (plan.entries[0].evidence.evidence_id,)
    persisted = ClaimEvidenceRegistry(tmp_path).load_evidence(result.evidence_ids[0])
    assert persisted == plan.entries[0].evidence


def test_existing_evidence_conflict_is_rejected(tmp_path: Path) -> None:
    bridge = setup_repository(tmp_path)
    plan = bridge.plan([output_selection()])
    ClaimEvidenceRegistry(tmp_path).save_evidence(plan.entries[0].evidence)

    with pytest.raises(ExperimentEvidenceConflictError):
        bridge.execute(plan, reviewed_digest=experiment_evidence_plan_digest(plan))
