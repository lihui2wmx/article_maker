from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .claim_evidence import Evidence, EvidenceKind, EvidenceSourceRef
from .claim_registry import (
    ClaimEvidenceNotFoundError,
    ClaimEvidenceRegistry,
    GraphAuditSeverity,
)
from .experiment import Experiment, ExperimentRun, experiment_spec_digest
from .experiment_registry import ExperimentNotFoundError, ExperimentRegistry
from .registration import ArtifactNotFoundError


class ExperimentEvidenceBridgeError(RuntimeError):
    """Base error for reviewed ExperimentRun-to-Evidence promotion."""


class ExperimentEvidenceEligibilityError(ExperimentEvidenceBridgeError):
    """Raised when a Run/Artifact selection cannot be promoted mechanically."""


class ExperimentEvidencePlanError(ExperimentEvidenceBridgeError):
    """Raised when an Experiment Evidence plan is invalid or ambiguous."""


class ExperimentEvidenceApprovalError(ExperimentEvidenceBridgeError):
    """Raised when execution is not bound to the exact reviewed plan."""


class ExperimentEvidenceStaleError(ExperimentEvidenceBridgeError):
    """Raised when Experiment, Run, or Artifact provenance changed after review."""


class ExperimentEvidenceConflictError(ExperimentEvidenceBridgeError):
    """Raised when a planned Evidence identity is already occupied."""


class ExperimentEvidencePostWriteError(ExperimentEvidenceBridgeError):
    """Raised when persisted Evidence differs from the reviewed preview or fails audit."""


class ExperimentEvidenceRole(StrEnum):
    OUTPUT = "output"
    DIAGNOSTIC = "diagnostic"


@dataclass(frozen=True, slots=True)
class ExperimentEvidenceSelection:
    experiment_id: str
    run_id: str
    artifact_id: str
    locator: str | None = None


@dataclass(frozen=True, slots=True)
class PlannedExperimentEvidence:
    experiment_id: str
    run_id: str
    artifact_id: str
    locator: str | None
    role: ExperimentEvidenceRole
    experiment_digest: str
    run_digest: str
    artifact_manifest_digest: str
    evidence: Evidence


@dataclass(frozen=True, slots=True)
class ExperimentEvidencePlan:
    entries: tuple[PlannedExperimentEvidence, ...]


@dataclass(frozen=True, slots=True)
class ExperimentEvidenceExecutionResult:
    plan_digest: str
    evidence_ids: tuple[str, ...]


def _canonical_model_bytes(model: BaseModel) -> bytes:
    return json.dumps(
        model.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _model_digest(model: BaseModel) -> str:
    return hashlib.sha256(_canonical_model_bytes(model)).hexdigest()


def generated_experiment_evidence_id(
    experiment_id: str,
    run_id: str,
    artifact_id: str,
    role: ExperimentEvidenceRole,
    locator: str | None,
) -> str:
    payload = {
        "bridge_version": "1",
        "experiment_id": experiment_id,
        "run_id": run_id,
        "artifact_id": artifact_id,
        "role": role.value,
        "locator": locator,
    }
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return f"ev-exp-{hashlib.sha256(serialized).hexdigest()[:24]}"


def _artifact_role(run: ExperimentRun, artifact_id: str) -> ExperimentEvidenceRole:
    in_output = artifact_id in run.output_artifact_ids
    diagnostics = (
        set(run.termination.diagnostic_artifact_ids)
        if run.termination is not None
        else set()
    )
    in_diagnostic = artifact_id in diagnostics

    if in_output and in_diagnostic:
        raise ExperimentEvidenceEligibilityError(
            f"Artifact is ambiguous because it is both output and diagnostic provenance: {artifact_id}"
        )
    if in_output:
        return ExperimentEvidenceRole.OUTPUT
    if in_diagnostic:
        return ExperimentEvidenceRole.DIAGNOSTIC
    raise ExperimentEvidenceEligibilityError(
        f"Artifact is not output or diagnostic provenance of Run {run.run_id}: {artifact_id}"
    )


def _preview_evidence(
    experiment: Experiment,
    run: ExperimentRun,
    artifact_id: str,
    locator: str | None,
    role: ExperimentEvidenceRole,
    *,
    artifact_manifest_digest: str,
) -> Evidence:
    source = EvidenceSourceRef(artifact_id=artifact_id, locator=locator)
    evidence_id = generated_experiment_evidence_id(
        experiment.experiment_id,
        run.run_id,
        artifact_id,
        role,
        locator,
    )
    location_text = f" at {locator}" if locator is not None else ""
    description = (
        f"ExperimentRun {run.run_id} {role.value} Artifact {artifact_id}{location_text}"
    )
    kind = (
        EvidenceKind.EXPERIMENT_RESULT
        if role is ExperimentEvidenceRole.OUTPUT
        else EvidenceKind.OTHER
    )
    return Evidence(
        schema_version="1.0",
        evidence_id=evidence_id,
        kind=kind,
        description=description,
        recorded_by=run.executed_by,
        sources=[source],
        metadata={
            "experiment_bridge": {
                "experiment_id": experiment.experiment_id,
                "run_id": run.run_id,
                "experiment_spec_digest": run.experiment_spec_digest,
                "run_status": run.status.value,
                "artifact_id": artifact_id,
                "artifact_role": role.value,
                "locator": locator,
                "run_digest": _model_digest(run),
                "artifact_manifest_digest": artifact_manifest_digest,
            }
        },
    )


def experiment_evidence_plan_digest(plan: ExperimentEvidencePlan) -> str:
    payload = [
        {
            "experiment_id": entry.experiment_id,
            "run_id": entry.run_id,
            "artifact_id": entry.artifact_id,
            "locator": entry.locator,
            "role": entry.role.value,
            "experiment_digest": entry.experiment_digest,
            "run_digest": entry.run_digest,
            "artifact_manifest_digest": entry.artifact_manifest_digest,
            "evidence": entry.evidence.model_dump(mode="json"),
        }
        for entry in plan.entries
    ]
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


class ExperimentEvidenceBridge:
    """Plan and execute reviewed promotion of explicit Run Artifacts into Evidence."""

    def __init__(self, repository_root: Path | str):
        self.experiment_registry = ExperimentRegistry(repository_root)
        self.claim_registry = ClaimEvidenceRegistry(repository_root)
        self.artifact_registry = self.experiment_registry.artifact_registry

    def _load_pair(self, experiment_id: str, run_id: str) -> tuple[Experiment, ExperimentRun]:
        try:
            experiment = self.experiment_registry.load_experiment(experiment_id)
            run = self.experiment_registry.load_run(experiment_id, run_id)
        except (ExperimentNotFoundError, ValidationError, ValueError) as exc:
            raise ExperimentEvidenceEligibilityError(
                f"Experiment/Run source records are unavailable or invalid: {experiment_id}/{run_id}"
            ) from exc

        if run.experiment_id != experiment.experiment_id:
            raise ExperimentEvidenceEligibilityError(
                f"Run {run.run_id} does not belong to Experiment {experiment.experiment_id}"
            )
        if run.experiment_spec_digest != experiment_spec_digest(experiment):
            raise ExperimentEvidenceEligibilityError(
                f"Run {run.run_id} is bound to a different Experiment specification digest"
            )
        return experiment, run

    def _load_clean_artifact(self, artifact_id: str):
        try:
            manifest = self.artifact_registry.load(artifact_id)
        except (ArtifactNotFoundError, ValidationError, ValueError) as exc:
            raise ExperimentEvidenceEligibilityError(
                f"selected Artifact is unavailable or invalid: {artifact_id}"
            ) from exc

        findings = [
            finding
            for finding in self.artifact_registry.audit()
            if finding.artifact_id == artifact_id
        ]
        if findings:
            summary = "; ".join(finding.code for finding in findings)
            raise ExperimentEvidenceEligibilityError(
                f"selected Artifact fails provenance audit: {artifact_id} ({summary})"
            )
        return manifest

    def plan(self, selections: list[ExperimentEvidenceSelection]) -> ExperimentEvidencePlan:
        if not selections:
            raise ExperimentEvidencePlanError(
                "at least one Experiment Evidence selection is required"
            )

        entries: list[PlannedExperimentEvidence] = []
        seen_sources: set[tuple[str, str, str, str | None]] = set()
        seen_evidence_ids: set[str] = set()

        for selection in selections:
            if selection.locator is not None and not selection.locator.strip():
                raise ExperimentEvidencePlanError("selection locator must not be blank")

            source_key = (
                selection.experiment_id,
                selection.run_id,
                selection.artifact_id,
                selection.locator,
            )
            if source_key in seen_sources:
                raise ExperimentEvidencePlanError(
                    f"duplicate Experiment Evidence selection: {source_key}"
                )
            seen_sources.add(source_key)

            experiment, run = self._load_pair(selection.experiment_id, selection.run_id)
            role = _artifact_role(run, selection.artifact_id)
            manifest = self._load_clean_artifact(selection.artifact_id)
            manifest_digest = _model_digest(manifest)
            evidence = _preview_evidence(
                experiment,
                run,
                selection.artifact_id,
                selection.locator,
                role,
                artifact_manifest_digest=manifest_digest,
            )

            if evidence.evidence_id in seen_evidence_ids:
                raise ExperimentEvidencePlanError(
                    f"multiple selections resolve to Evidence ID {evidence.evidence_id}"
                )
            seen_evidence_ids.add(evidence.evidence_id)

            try:
                self.claim_registry.load_evidence(evidence.evidence_id)
            except ClaimEvidenceNotFoundError:
                pass
            else:
                raise ExperimentEvidenceConflictError(
                    f"Evidence already exists: {evidence.evidence_id}"
                )

            entries.append(
                PlannedExperimentEvidence(
                    experiment_id=experiment.experiment_id,
                    run_id=run.run_id,
                    artifact_id=selection.artifact_id,
                    locator=selection.locator,
                    role=role,
                    experiment_digest=_model_digest(experiment),
                    run_digest=_model_digest(run),
                    artifact_manifest_digest=manifest_digest,
                    evidence=evidence,
                )
            )

        entries.sort(
            key=lambda entry: (
                entry.experiment_id,
                entry.run_id,
                entry.artifact_id,
                entry.locator or "",
            )
        )
        return ExperimentEvidencePlan(entries=tuple(entries))

    def execute(
        self,
        plan: ExperimentEvidencePlan,
        *,
        reviewed_digest: str,
    ) -> ExperimentEvidenceExecutionResult:
        snapshot = copy.deepcopy(plan)
        actual_digest = experiment_evidence_plan_digest(snapshot)
        if reviewed_digest != actual_digest:
            raise ExperimentEvidenceApprovalError(
                "reviewed_digest does not match the exact Experiment Evidence plan"
            )
        if not snapshot.entries:
            raise ExperimentEvidencePlanError(
                "cannot execute an empty Experiment Evidence plan"
            )

        for entry in snapshot.entries:
            experiment, run = self._load_pair(entry.experiment_id, entry.run_id)
            if _model_digest(experiment) != entry.experiment_digest:
                raise ExperimentEvidenceStaleError(
                    f"Experiment changed after review: {entry.experiment_id}"
                )
            if _model_digest(run) != entry.run_digest:
                raise ExperimentEvidenceStaleError(
                    f"ExperimentRun changed after review: {entry.run_id}"
                )

            role = _artifact_role(run, entry.artifact_id)
            if role is not entry.role:
                raise ExperimentEvidenceStaleError(
                    f"Artifact provenance role changed after review: {entry.artifact_id}"
                )
            manifest = self._load_clean_artifact(entry.artifact_id)
            manifest_digest = _model_digest(manifest)
            if manifest_digest != entry.artifact_manifest_digest:
                raise ExperimentEvidenceStaleError(
                    f"Artifact manifest changed after review: {entry.artifact_id}"
                )

            regenerated = _preview_evidence(
                experiment,
                run,
                entry.artifact_id,
                entry.locator,
                role,
                artifact_manifest_digest=manifest_digest,
            )
            if regenerated.model_dump(mode="json") != entry.evidence.model_dump(mode="json"):
                raise ExperimentEvidencePlanError(
                    f"reviewed Evidence preview is not the deterministic projection of Run provenance: {entry.run_id}/{entry.artifact_id}"
                )

            try:
                self.claim_registry.load_evidence(entry.evidence.evidence_id)
            except ClaimEvidenceNotFoundError:
                pass
            else:
                raise ExperimentEvidenceConflictError(
                    f"Evidence already exists: {entry.evidence.evidence_id}"
                )

        written_paths: list[Path] = []
        try:
            for entry in snapshot.entries:
                self.claim_registry.save_evidence(entry.evidence)
                written_paths.append(
                    self.claim_registry.evidence_dir / f"{entry.evidence.evidence_id}.json"
                )
        except Exception:
            for path in reversed(written_paths):
                path.unlink(missing_ok=True)
            raise

        try:
            for entry in snapshot.entries:
                persisted = self.claim_registry.load_evidence(entry.evidence.evidence_id)
                if persisted.model_dump(mode="json") != entry.evidence.model_dump(mode="json"):
                    raise ExperimentEvidencePostWriteError(
                        f"persisted Evidence differs from reviewed preview: {entry.evidence.evidence_id}"
                    )

            new_ids = {entry.evidence.evidence_id for entry in snapshot.entries}
            structural = [
                finding
                for finding in self.claim_registry.audit()
                if finding.record_id in new_ids and finding.severity is GraphAuditSeverity.ERROR
            ]
            if structural:
                summary = "; ".join(
                    f"{finding.record_id}:{finding.code}" for finding in structural
                )
                raise ExperimentEvidencePostWriteError(
                    f"post-write graph audit found structural errors: {summary}"
                )
        except Exception:
            for path in reversed(written_paths):
                path.unlink(missing_ok=True)
            raise

        return ExperimentEvidenceExecutionResult(
            plan_digest=actual_digest,
            evidence_ids=tuple(entry.evidence.evidence_id for entry in snapshot.entries),
        )
