from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TypeVar

from pydantic import BaseModel, ValidationError

from .registration import ArtifactNotFoundError, ArtifactRegistry
from .research_state import (
    Decision,
    DecisionOutcome,
    DecisionSubjectType,
    Hypothesis,
    ResearchQuestion,
    ResearchStateStatus,
    validate_decision_id,
    validate_hypothesis_id,
    validate_research_question_id,
)

DEFAULT_RESEARCH_STATE_PATH = "research"


class ResearchStateRegistryError(RuntimeError):
    """Base error for filesystem-backed research-state persistence."""


class ResearchStateNotFoundError(ResearchStateRegistryError):
    """Raised when a requested research-state record does not exist."""


@dataclass(frozen=True, slots=True)
class ResearchStateAuditFinding:
    record_id: str
    code: str
    message: str


_ModelT = TypeVar("_ModelT", bound=BaseModel)

_EXPECTED_STATUS: dict[DecisionOutcome, ResearchStateStatus] = {
    DecisionOutcome.APPROVE: ResearchStateStatus.ACCEPTED,
    DecisionOutcome.REJECT: ResearchStateStatus.REJECTED,
    DecisionOutcome.SUPERSEDE: ResearchStateStatus.SUPERSEDED,
}


class ResearchStateRegistry:
    """Persist and audit repository-level ResearchQuestion/Hypothesis/Decision state."""

    def __init__(
        self,
        repository_root: Path | str,
        research_state_path: str = DEFAULT_RESEARCH_STATE_PATH,
    ):
        try:
            self.repository_root = Path(repository_root).resolve(strict=True)
        except OSError as exc:
            raise ResearchStateRegistryError(
                "repository_root must be an existing directory"
            ) from exc
        if not self.repository_root.is_dir():
            raise ResearchStateRegistryError("repository_root must be an existing directory")

        if research_state_path.startswith("/") or ".." in Path(research_state_path).parts:
            raise ResearchStateRegistryError(
                "research_state_path must be repository-relative and must not traverse upward"
            )

        self.research_root = self.repository_root / research_state_path
        try:
            self.research_root.resolve(strict=False).relative_to(self.repository_root)
        except ValueError as exc:
            raise ResearchStateRegistryError(
                "research_state_path resolves outside repository_root"
            ) from exc

        self.questions_dir = self.research_root / "questions"
        self.hypotheses_dir = self.research_root / "hypotheses"
        self.decisions_dir = self.research_root / "decisions"
        self.artifact_registry = ArtifactRegistry(self.repository_root)

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

    def _write(self, directory: Path, record_id: str, model: BaseModel) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{record_id}.json"
        serialized = self._canonical_json(model)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=f".{record_id}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(serialized)
            temporary_path = Path(stream.name)

        try:
            os.replace(temporary_path, target)
        finally:
            temporary_path.unlink(missing_ok=True)

    def save_question(self, question: ResearchQuestion) -> ResearchQuestion:
        self._write(self.questions_dir, question.research_question_id, question)
        return question

    def save_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis:
        self._write(self.hypotheses_dir, hypothesis.hypothesis_id, hypothesis)
        return hypothesis

    def save_decision(self, decision: Decision) -> Decision:
        self._write(self.decisions_dir, decision.decision_id, decision)
        return decision

    @staticmethod
    def _load(path: Path, model_type: type[_ModelT], record_id: str) -> _ModelT:
        if not path.is_file():
            raise ResearchStateNotFoundError(f"research-state record not found: {record_id}")
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))

    def load_question(self, research_question_id: str) -> ResearchQuestion:
        validate_research_question_id(research_question_id)
        return self._load(
            self.questions_dir / f"{research_question_id}.json",
            ResearchQuestion,
            research_question_id,
        )

    def load_hypothesis(self, hypothesis_id: str) -> Hypothesis:
        validate_hypothesis_id(hypothesis_id)
        return self._load(
            self.hypotheses_dir / f"{hypothesis_id}.json",
            Hypothesis,
            hypothesis_id,
        )

    def load_decision(self, decision_id: str) -> Decision:
        validate_decision_id(decision_id)
        return self._load(
            self.decisions_dir / f"{decision_id}.json",
            Decision,
            decision_id,
        )

    @staticmethod
    def _iter_json(directory: Path) -> Iterable[Path]:
        if not directory.exists():
            return ()
        return tuple(sorted(directory.glob("*.json")))

    def list_questions(self) -> list[ResearchQuestion]:
        return [
            ResearchQuestion.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self._iter_json(self.questions_dir)
        ]

    def list_hypotheses(self) -> list[Hypothesis]:
        return [
            Hypothesis.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self._iter_json(self.hypotheses_dir)
        ]

    def list_decisions(self) -> list[Decision]:
        return [
            Decision.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self._iter_json(self.decisions_dir)
        ]

    @staticmethod
    def _record_id(model: BaseModel) -> str:
        if isinstance(model, ResearchQuestion):
            return model.research_question_id
        if isinstance(model, Hypothesis):
            return model.hypothesis_id
        if isinstance(model, Decision):
            return model.decision_id
        raise TypeError(f"unsupported research-state model: {type(model)!r}")

    def _audit_collection(
        self,
        directory: Path,
        model_type: type[_ModelT],
    ) -> tuple[dict[str, _ModelT], list[ResearchStateAuditFinding]]:
        records: dict[str, _ModelT] = {}
        findings: list[ResearchStateAuditFinding] = []

        for path in self._iter_json(directory):
            try:
                model = model_type.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValidationError, ValueError) as exc:
                findings.append(
                    ResearchStateAuditFinding(
                        path.stem,
                        "invalid-record",
                        f"record cannot be parsed as {model_type.__name__}: {exc}",
                    )
                )
                continue

            record_id = self._record_id(model)
            if path.stem != record_id:
                findings.append(
                    ResearchStateAuditFinding(
                        record_id,
                        "filename-id-mismatch",
                        f"record filename {path.name} does not match canonical ID {record_id}",
                    )
                )
            if record_id in records:
                findings.append(
                    ResearchStateAuditFinding(
                        record_id,
                        "duplicate-id",
                        f"multiple repository records resolve to ID {record_id}",
                    )
                )
                continue
            records[record_id] = model

        return records, findings

    def _artifact_findings(
        self,
        record_id: str,
        artifact_refs: list[str],
    ) -> list[ResearchStateAuditFinding]:
        findings: list[ResearchStateAuditFinding] = []
        for artifact_id in artifact_refs:
            try:
                self.artifact_registry.load(artifact_id)
            except (ArtifactNotFoundError, ValidationError, ValueError) as exc:
                findings.append(
                    ResearchStateAuditFinding(
                        record_id,
                        "missing-artifact",
                        f"referenced artifact is unavailable or invalid: {artifact_id} ({exc})",
                    )
                )
        return findings

    @staticmethod
    def _subject_key(decision: Decision) -> tuple[DecisionSubjectType, str]:
        return decision.subject_type, decision.subject_id

    def audit(self) -> list[ResearchStateAuditFinding]:
        """Resolve repository-level references and report graph-integrity violations."""

        questions, findings = self._audit_collection(self.questions_dir, ResearchQuestion)
        hypotheses, hypothesis_findings = self._audit_collection(
            self.hypotheses_dir, Hypothesis
        )
        decisions, decision_findings = self._audit_collection(self.decisions_dir, Decision)
        findings.extend(hypothesis_findings)
        findings.extend(decision_findings)

        for question in questions.values():
            findings.extend(
                self._artifact_findings(question.research_question_id, question.artifact_refs)
            )

        for hypothesis in hypotheses.values():
            findings.extend(
                self._artifact_findings(hypothesis.hypothesis_id, hypothesis.artifact_refs)
            )
            if hypothesis.research_question_id not in questions:
                findings.append(
                    ResearchStateAuditFinding(
                        hypothesis.hypothesis_id,
                        "missing-research-question",
                        "hypothesis references an unavailable ResearchQuestion: "
                        f"{hypothesis.research_question_id}",
                    )
                )

        for decision in decisions.values():
            findings.extend(
                self._artifact_findings(decision.decision_id, decision.artifact_refs)
            )
            if decision.subject_type is DecisionSubjectType.RESEARCH_QUESTION:
                subject_exists = decision.subject_id in questions
            else:
                subject_exists = decision.subject_id in hypotheses
            if not subject_exists:
                findings.append(
                    ResearchStateAuditFinding(
                        decision.decision_id,
                        "missing-decision-subject",
                        f"decision subject is unavailable: {decision.subject_id}",
                    )
                )

        governed: dict[tuple[DecisionSubjectType, str], ResearchQuestion | Hypothesis] = {
            (DecisionSubjectType.RESEARCH_QUESTION, question.research_question_id): question
            for question in questions.values()
        }
        governed.update(
            {
                (DecisionSubjectType.HYPOTHESIS, hypothesis.hypothesis_id): hypothesis
                for hypothesis in hypotheses.values()
            }
        )

        decisions_by_subject: dict[tuple[DecisionSubjectType, str], list[Decision]] = defaultdict(list)
        for decision in decisions.values():
            decisions_by_subject[self._subject_key(decision)].append(decision)

        for subject_key, subject in governed.items():
            subject_id = subject_key[1]
            subject_decisions = decisions_by_subject.get(subject_key, [])

            if subject.status is ResearchStateStatus.PROPOSED:
                if subject_decisions:
                    findings.append(
                        ResearchStateAuditFinding(
                            subject_id,
                            "decision-on-proposed-state",
                            "proposed object has Decision records but no canonical governed transition",
                        )
                    )
                continue

            governing_id = subject.governing_decision_id
            if governing_id not in decisions:
                findings.append(
                    ResearchStateAuditFinding(
                        subject_id,
                        "missing-governing-decision",
                        f"governing Decision is unavailable: {governing_id}",
                    )
                )
                continue

            governing = decisions[governing_id]
            if self._subject_key(governing) != subject_key:
                findings.append(
                    ResearchStateAuditFinding(
                        subject_id,
                        "decision-subject-mismatch",
                        f"governing Decision {governing_id} points to {governing.subject_id}",
                    )
                )
            expected_status = _EXPECTED_STATUS[governing.outcome]
            if subject.status is not expected_status:
                findings.append(
                    ResearchStateAuditFinding(
                        subject_id,
                        "decision-outcome-mismatch",
                        f"status {subject.status.value} does not match governing Decision "
                        f"outcome {governing.outcome.value}",
                    )
                )

        for subject_key, subject_decisions in decisions_by_subject.items():
            group_ids = {decision.decision_id for decision in subject_decisions}
            children: dict[str, list[str]] = defaultdict(list)
            valid_previous_edges: set[tuple[str, str]] = set()

            for decision in subject_decisions:
                previous_id = decision.previous_decision_id
                if previous_id is None:
                    continue
                previous = decisions.get(previous_id)
                if previous is None:
                    findings.append(
                        ResearchStateAuditFinding(
                            decision.decision_id,
                            "missing-previous-decision",
                            f"previous Decision is unavailable: {previous_id}",
                        )
                    )
                    continue
                if self._subject_key(previous) != subject_key:
                    findings.append(
                        ResearchStateAuditFinding(
                            decision.decision_id,
                            "previous-decision-subject-mismatch",
                            f"previous Decision {previous_id} governs a different subject",
                        )
                    )
                    continue
                if previous.decided_at >= decision.decided_at:
                    findings.append(
                        ResearchStateAuditFinding(
                            decision.decision_id,
                            "decision-time-order",
                            f"Decision {decision.decision_id} must occur after {previous_id}",
                        )
                    )
                children[previous_id].append(decision.decision_id)
                valid_previous_edges.add((decision.decision_id, previous_id))

            for previous_id, child_ids in children.items():
                if len(child_ids) > 1:
                    findings.append(
                        ResearchStateAuditFinding(
                            previous_id,
                            "decision-history-branch",
                            "Decision history branches to multiple successors: "
                            + ", ".join(sorted(child_ids)),
                        )
                    )

            for decision in subject_decisions:
                seen: set[str] = set()
                current = decision
                while current.previous_decision_id is not None:
                    if current.decision_id in seen:
                        findings.append(
                            ResearchStateAuditFinding(
                                decision.decision_id,
                                "decision-history-cycle",
                                "Decision history contains a cycle",
                            )
                        )
                        break
                    seen.add(current.decision_id)
                    previous = decisions.get(current.previous_decision_id)
                    if previous is None or self._subject_key(previous) != subject_key:
                        break
                    current = previous

            roots = [
                decision.decision_id
                for decision in subject_decisions
                if decision.previous_decision_id is None
            ]
            if len(subject_decisions) > 1 and len(roots) != 1:
                findings.append(
                    ResearchStateAuditFinding(
                        subject_key[1],
                        "decision-history-roots",
                        "Decision history must have exactly one root when multiple decisions exist",
                    )
                )

            referenced_previous = {
                previous_id for _, previous_id in valid_previous_edges if previous_id in group_ids
            }
            heads = sorted(group_ids - referenced_previous)
            if len(heads) != 1:
                findings.append(
                    ResearchStateAuditFinding(
                        subject_key[1],
                        "decision-history-heads",
                        "Decision history must have exactly one current head; found: "
                        + ", ".join(heads),
                    )
                )
                continue

            subject = governed.get(subject_key)
            if (
                subject is not None
                and subject.status is not ResearchStateStatus.PROPOSED
                and subject.governing_decision_id != heads[0]
            ):
                findings.append(
                    ResearchStateAuditFinding(
                        subject_key[1],
                        "stale-governing-decision",
                        f"governing_decision_id must reference Decision-history head {heads[0]}",
                    )
                )

        return sorted(findings, key=lambda item: (item.record_id, item.code, item.message))
