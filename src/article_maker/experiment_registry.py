from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable, TypeVar

from pydantic import BaseModel, ValidationError

from .experiment import Experiment, ExperimentRun, experiment_spec_digest
from .registration import ArtifactNotFoundError, ArtifactRegistry
from .scientific_ids import validate_experiment_id, validate_experiment_run_id

DEFAULT_EXPERIMENTS_PATH = "experiments"


class ExperimentRegistryError(RuntimeError):
    """Base error for filesystem-backed Experiment persistence."""


class ExperimentNotFoundError(ExperimentRegistryError):
    """Raised when a requested Experiment or ExperimentRun is unavailable."""


class ExperimentAuditSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ExperimentAuditFinding:
    record_id: str
    code: str
    message: str
    severity: ExperimentAuditSeverity = ExperimentAuditSeverity.ERROR


_ModelT = TypeVar("_ModelT", bound=BaseModel)


class ExperimentRegistry:
    """Persist and audit repository-level Experiment and ExperimentRun state."""

    def __init__(
        self,
        repository_root: Path | str,
        *,
        experiments_path: str = DEFAULT_EXPERIMENTS_PATH,
    ):
        try:
            self.repository_root = Path(repository_root).resolve(strict=True)
        except OSError as exc:
            raise ExperimentRegistryError(
                "repository_root must be an existing directory"
            ) from exc
        if not self.repository_root.is_dir():
            raise ExperimentRegistryError(
                "repository_root must be an existing directory"
            )

        self.experiments_root = self._resolve_repository_directory(experiments_path)
        self.artifact_registry = ArtifactRegistry(self.repository_root)

    def _resolve_repository_directory(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ExperimentRegistryError(
                "registry paths must be repository-relative and must not traverse upward"
            )
        resolved = (self.repository_root / candidate).resolve(strict=False)
        try:
            resolved.relative_to(self.repository_root)
        except ValueError as exc:
            raise ExperimentRegistryError(
                "registry path resolves outside repository_root"
            ) from exc
        return resolved

    @staticmethod
    def _canonical_json(model: BaseModel) -> str:
        return (
            json.dumps(
                model.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n"
        )

    def _write(self, directory: Path, filename: str, model: BaseModel) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / filename
        serialized = self._canonical_json(model)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=f".{filename}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(serialized)
            temporary_path = Path(stream.name)

        try:
            os.replace(temporary_path, target)
        finally:
            temporary_path.unlink(missing_ok=True)

    def save_experiment(self, experiment: Experiment) -> Experiment:
        directory = self.experiments_root / experiment.experiment_id
        self._write(directory, "experiment.json", experiment)
        return experiment

    def save_run(self, run: ExperimentRun) -> ExperimentRun:
        directory = self.experiments_root / run.experiment_id / "runs"
        self._write(directory, f"{run.run_id}.json", run)
        return run

    @staticmethod
    def _load(path: Path, model_type: type[_ModelT], record_id: str) -> _ModelT:
        if not path.is_file():
            raise ExperimentNotFoundError(f"experiment record not found: {record_id}")
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))

    def load_experiment(self, experiment_id: str) -> Experiment:
        validate_experiment_id(experiment_id)
        return self._load(
            self.experiments_root / experiment_id / "experiment.json",
            Experiment,
            experiment_id,
        )

    def load_run(self, experiment_id: str, run_id: str) -> ExperimentRun:
        validate_experiment_id(experiment_id)
        validate_experiment_run_id(run_id)
        return self._load(
            self.experiments_root / experiment_id / "runs" / f"{run_id}.json",
            ExperimentRun,
            run_id,
        )

    @staticmethod
    def _iter_experiment_dirs(root: Path) -> tuple[Path, ...]:
        if not root.exists():
            return ()
        return tuple(sorted(path for path in root.iterdir() if path.is_dir()))

    @staticmethod
    def _iter_json(directory: Path) -> Iterable[Path]:
        if not directory.exists():
            return ()
        return tuple(sorted(directory.glob("*.json")))

    def list_experiments(self) -> list[Experiment]:
        records: list[Experiment] = []
        for directory in self._iter_experiment_dirs(self.experiments_root):
            path = directory / "experiment.json"
            if path.is_file():
                records.append(
                    Experiment.model_validate_json(path.read_text(encoding="utf-8"))
                )
        return records

    def list_runs(self) -> list[ExperimentRun]:
        records: list[ExperimentRun] = []
        for directory in self._iter_experiment_dirs(self.experiments_root):
            for path in self._iter_json(directory / "runs"):
                records.append(
                    ExperimentRun.model_validate_json(path.read_text(encoding="utf-8"))
                )
        return records

    def _artifact_exists(self, artifact_id: str) -> bool:
        try:
            self.artifact_registry.load(artifact_id)
        except (ArtifactNotFoundError, ValidationError, ValueError):
            return False
        return True

    def _artifact_findings(
        self,
        record_id: str,
        artifact_ids: Iterable[str],
        *,
        role: str,
    ) -> list[ExperimentAuditFinding]:
        findings: list[ExperimentAuditFinding] = []
        for artifact_id in artifact_ids:
            if not self._artifact_exists(artifact_id):
                findings.append(
                    ExperimentAuditFinding(
                        record_id,
                        "missing-artifact",
                        f"{role} Artifact is unavailable or invalid: {artifact_id}",
                    )
                )
        return findings

    def _experiment_artifact_findings(
        self, experiment: Experiment
    ) -> list[ExperimentAuditFinding]:
        findings: list[ExperimentAuditFinding] = []
        findings.extend(
            self._artifact_findings(
                experiment.experiment_id,
                experiment.input_artifact_ids,
                role="experiment input",
            )
        )
        findings.extend(
            self._artifact_findings(
                experiment.experiment_id,
                experiment.config_artifact_ids,
                role="experiment config",
            )
        )
        findings.extend(
            self._artifact_findings(
                experiment.experiment_id,
                experiment.expected_code.code_artifact_ids,
                role="expected code",
            )
        )
        if experiment.expected_code.working_tree_diff_artifact_id is not None:
            findings.extend(
                self._artifact_findings(
                    experiment.experiment_id,
                    [experiment.expected_code.working_tree_diff_artifact_id],
                    role="expected dirty-code diff",
                )
            )
        findings.extend(
            self._artifact_findings(
                experiment.experiment_id,
                experiment.expected_environment.environment_artifact_ids,
                role="expected environment",
            )
        )
        return findings

    def _run_artifact_findings(
        self, run: ExperimentRun
    ) -> list[ExperimentAuditFinding]:
        findings: list[ExperimentAuditFinding] = []
        groups: list[tuple[str, Iterable[str]]] = [
            ("run input", run.input_artifact_ids),
            ("run config", run.config_artifact_ids),
            ("run code", run.code.code_artifact_ids),
            ("run environment", run.environment.environment_artifact_ids),
            ("run output", run.output_artifact_ids),
        ]
        if run.code.working_tree_diff_artifact_id is not None:
            groups.append(
                ("run dirty-code diff", [run.code.working_tree_diff_artifact_id])
            )
        if run.termination is not None:
            groups.append(
                ("run diagnostic", run.termination.diagnostic_artifact_ids)
            )
        for role, artifact_ids in groups:
            findings.extend(
                self._artifact_findings(run.run_id, artifact_ids, role=role)
            )
        return findings

    @staticmethod
    def _lineage_cycle_findings(
        runs: dict[str, ExperimentRun],
    ) -> list[ExperimentAuditFinding]:
        findings: list[ExperimentAuditFinding] = []
        state: dict[str, int] = {}
        stack: list[str] = []
        reported: set[tuple[str, ...]] = set()

        def visit(run_id: str) -> None:
            state[run_id] = 1
            stack.append(run_id)
            run = runs[run_id]
            parent_id = run.lineage.parent_run_id if run.lineage is not None else None
            if parent_id in runs:
                parent_state = state.get(parent_id, 0)
                if parent_state == 0:
                    visit(parent_id)
                elif parent_state == 1:
                    start = stack.index(parent_id)
                    cycle = stack[start:] + [parent_id]
                    members = tuple(sorted(set(cycle)))
                    if members not in reported:
                        reported.add(members)
                        message = "ExperimentRun lineage cycle detected: " + " -> ".join(cycle)
                        for member in members:
                            findings.append(
                                ExperimentAuditFinding(
                                    member,
                                    "run-lineage-cycle",
                                    message,
                                )
                            )
            stack.pop()
            state[run_id] = 2

        for run_id in sorted(runs):
            if state.get(run_id, 0) == 0:
                visit(run_id)

        return findings

    def audit(self) -> list[ExperimentAuditFinding]:
        """Audit Experiment persistence and provenance integrity without mutation."""

        findings: list[ExperimentAuditFinding] = []
        experiments: dict[str, Experiment] = {}
        runs: dict[str, ExperimentRun] = {}

        for directory in self._iter_experiment_dirs(self.experiments_root):
            experiment_path = directory / "experiment.json"
            if experiment_path.is_file():
                try:
                    experiment = Experiment.model_validate_json(
                        experiment_path.read_text(encoding="utf-8")
                    )
                except (OSError, UnicodeError, ValidationError, ValueError) as exc:
                    findings.append(
                        ExperimentAuditFinding(
                            directory.name,
                            "invalid-experiment-record",
                            f"experiment.json cannot be parsed as Experiment: {exc}",
                        )
                    )
                else:
                    if directory.name != experiment.experiment_id:
                        findings.append(
                            ExperimentAuditFinding(
                                experiment.experiment_id,
                                "experiment-directory-id-mismatch",
                                f"directory {directory.name} does not match Experiment ID "
                                f"{experiment.experiment_id}",
                            )
                        )
                    if experiment.experiment_id in experiments:
                        findings.append(
                            ExperimentAuditFinding(
                                experiment.experiment_id,
                                "duplicate-experiment-id",
                                "multiple repository records resolve to this Experiment ID",
                            )
                        )
                    else:
                        experiments[experiment.experiment_id] = experiment

            for run_path in self._iter_json(directory / "runs"):
                try:
                    run = ExperimentRun.model_validate_json(
                        run_path.read_text(encoding="utf-8")
                    )
                except (OSError, UnicodeError, ValidationError, ValueError) as exc:
                    findings.append(
                        ExperimentAuditFinding(
                            run_path.stem,
                            "invalid-run-record",
                            f"run record cannot be parsed as ExperimentRun: {exc}",
                        )
                    )
                    continue

                if run_path.stem != run.run_id:
                    findings.append(
                        ExperimentAuditFinding(
                            run.run_id,
                            "run-filename-id-mismatch",
                            f"run filename {run_path.name} does not match Run ID {run.run_id}",
                        )
                    )
                if directory.name != run.experiment_id:
                    findings.append(
                        ExperimentAuditFinding(
                            run.run_id,
                            "run-experiment-directory-mismatch",
                            f"run stored under {directory.name} but references Experiment "
                            f"{run.experiment_id}",
                        )
                    )
                if run.run_id in runs:
                    findings.append(
                        ExperimentAuditFinding(
                            run.run_id,
                            "duplicate-run-id",
                            "multiple repository records resolve to this ExperimentRun ID",
                        )
                    )
                else:
                    runs[run.run_id] = run

        for experiment in experiments.values():
            findings.extend(self._experiment_artifact_findings(experiment))

        for run in runs.values():
            experiment = experiments.get(run.experiment_id)
            if experiment is None:
                findings.append(
                    ExperimentAuditFinding(
                        run.run_id,
                        "missing-experiment",
                        f"referenced Experiment is unavailable: {run.experiment_id}",
                    )
                )
            else:
                current_digest = experiment_spec_digest(experiment)
                if run.experiment_spec_digest != current_digest:
                    findings.append(
                        ExperimentAuditFinding(
                            run.run_id,
                            "experiment-spec-digest-mismatch",
                            f"Run binds to {run.experiment_spec_digest} but canonical Experiment "
                            f"{run.experiment_id} currently hashes to {current_digest}",
                        )
                    )

            findings.extend(self._run_artifact_findings(run))

            if run.lineage is not None and run.lineage.parent_run_id not in runs:
                findings.append(
                    ExperimentAuditFinding(
                        run.run_id,
                        "missing-lineage-parent",
                        f"lineage parent Run is unavailable: {run.lineage.parent_run_id}",
                    )
                )

        findings.extend(self._lineage_cycle_findings(runs))

        return sorted(
            findings,
            key=lambda item: (
                item.severity.value,
                item.record_id,
                item.code,
                item.message,
            ),
        )
