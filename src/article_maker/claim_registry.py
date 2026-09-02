from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable, TypeVar

from pydantic import BaseModel, ValidationError

from .claim_evidence import (
    Claim,
    ClaimEvidenceLink,
    ClaimStatus,
    Evidence,
    EvidenceRelation,
    RelationStatus,
)
from .registration import ArtifactNotFoundError, ArtifactRegistry
from .research_state import (
    Decision,
    DecisionOutcome,
    DecisionSubjectType,
    Hypothesis,
    ResearchQuestion,
)
from .scientific_ids import (
    validate_claim_evidence_link_id,
    validate_claim_id,
    validate_evidence_id,
)

DEFAULT_CLAIMS_PATH = "claims"
DEFAULT_EVIDENCE_PATH = "evidence"
DEFAULT_RESEARCH_PATH = "research"


class ClaimEvidenceRegistryError(RuntimeError):
    """Base error for filesystem-backed Claim/Evidence persistence."""


class ClaimEvidenceNotFoundError(ClaimEvidenceRegistryError):
    """Raised when a requested Claim/Evidence record is unavailable."""


class GraphAuditSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ClaimEvidenceAuditFinding:
    record_id: str
    code: str
    message: str
    severity: GraphAuditSeverity = GraphAuditSeverity.ERROR


_ModelT = TypeVar("_ModelT", bound=BaseModel)

_CLAIM_EXPECTED_STATUS: dict[DecisionOutcome, ClaimStatus] = {
    DecisionOutcome.APPROVE: ClaimStatus.APPROVED,
    DecisionOutcome.REJECT: ClaimStatus.REJECTED,
    DecisionOutcome.SUPERSEDE: ClaimStatus.SUPERSEDED,
}

_LINK_EXPECTED_STATUS: dict[DecisionOutcome, RelationStatus] = {
    DecisionOutcome.APPROVE: RelationStatus.ACCEPTED,
    DecisionOutcome.REJECT: RelationStatus.REJECTED,
    DecisionOutcome.SUPERSEDE: RelationStatus.SUPERSEDED,
}

_PHASE3_SUBJECT_TYPES = {
    DecisionSubjectType.CLAIM,
    DecisionSubjectType.CLAIM_EVIDENCE_LINK,
}


class ClaimEvidenceRegistry:
    """Persist and audit repository-level Claim/Evidence scientific graph state."""

    def __init__(
        self,
        repository_root: Path | str,
        *,
        claims_path: str = DEFAULT_CLAIMS_PATH,
        evidence_path: str = DEFAULT_EVIDENCE_PATH,
        research_path: str = DEFAULT_RESEARCH_PATH,
    ):
        try:
            self.repository_root = Path(repository_root).resolve(strict=True)
        except OSError as exc:
            raise ClaimEvidenceRegistryError(
                "repository_root must be an existing directory"
            ) from exc
        if not self.repository_root.is_dir():
            raise ClaimEvidenceRegistryError(
                "repository_root must be an existing directory"
            )

        self.claims_dir = self._resolve_repository_directory(claims_path)
        self.evidence_dir = self._resolve_repository_directory(evidence_path)
        self.links_dir = self.evidence_dir / "links"
        self.research_root = self._resolve_repository_directory(research_path)
        self.questions_dir = self.research_root / "questions"
        self.hypotheses_dir = self.research_root / "hypotheses"
        self.decisions_dir = self.research_root / "decisions"
        self.artifact_registry = ArtifactRegistry(self.repository_root)

    def _resolve_repository_directory(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ClaimEvidenceRegistryError(
                "registry paths must be repository-relative and must not traverse upward"
            )
        resolved = (self.repository_root / candidate).resolve(strict=False)
        try:
            resolved.relative_to(self.repository_root)
        except ValueError as exc:
            raise ClaimEvidenceRegistryError(
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

    def save_claim(self, claim: Claim) -> Claim:
        self._write(self.claims_dir, claim.claim_id, claim)
        return claim

    def save_evidence(self, evidence: Evidence) -> Evidence:
        self._write(self.evidence_dir, evidence.evidence_id, evidence)
        return evidence

    def save_link(self, link: ClaimEvidenceLink) -> ClaimEvidenceLink:
        self._write(self.links_dir, link.link_id, link)
        return link

    @staticmethod
    def _load(path: Path, model_type: type[_ModelT], record_id: str) -> _ModelT:
        if not path.is_file():
            raise ClaimEvidenceNotFoundError(
                f"Claim/Evidence record not found: {record_id}"
            )
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))

    def load_claim(self, claim_id: str) -> Claim:
        validate_claim_id(claim_id)
        return self._load(self.claims_dir / f"{claim_id}.json", Claim, claim_id)

    def load_evidence(self, evidence_id: str) -> Evidence:
        validate_evidence_id(evidence_id)
        return self._load(
            self.evidence_dir / f"{evidence_id}.json",
            Evidence,
            evidence_id,
        )

    def load_link(self, link_id: str) -> ClaimEvidenceLink:
        validate_claim_evidence_link_id(link_id)
        return self._load(
            self.links_dir / f"{link_id}.json",
            ClaimEvidenceLink,
            link_id,
        )

    @staticmethod
    def _iter_json(directory: Path) -> Iterable[Path]:
        if not directory.exists():
            return ()
        return tuple(sorted(directory.glob("*.json")))

    def list_claims(self) -> list[Claim]:
        return [
            Claim.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self._iter_json(self.claims_dir)
        ]

    def list_evidence(self) -> list[Evidence]:
        return [
            Evidence.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self._iter_json(self.evidence_dir)
        ]

    def list_links(self) -> list[ClaimEvidenceLink]:
        return [
            ClaimEvidenceLink.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self._iter_json(self.links_dir)
        ]

    @staticmethod
    def _record_id(model: BaseModel) -> str:
        if isinstance(model, Claim):
            return model.claim_id
        if isinstance(model, Evidence):
            return model.evidence_id
        if isinstance(model, ClaimEvidenceLink):
            return model.link_id
        if isinstance(model, ResearchQuestion):
            return model.research_question_id
        if isinstance(model, Hypothesis):
            return model.hypothesis_id
        if isinstance(model, Decision):
            return model.decision_id
        raise TypeError(f"unsupported graph model: {type(model)!r}")

    def _audit_collection(
        self,
        directory: Path,
        model_type: type[_ModelT],
        *,
        external: bool = False,
    ) -> tuple[dict[str, _ModelT], list[ClaimEvidenceAuditFinding]]:
        records: dict[str, _ModelT] = {}
        findings: list[ClaimEvidenceAuditFinding] = []

        for path in self._iter_json(directory):
            try:
                model = model_type.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValidationError, ValueError) as exc:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        path.stem,
                        "invalid-external-record" if external else "invalid-record",
                        f"record cannot be parsed as {model_type.__name__}: {exc}",
                    )
                )
                continue

            record_id = self._record_id(model)
            if path.stem != record_id:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        record_id,
                        "external-filename-id-mismatch"
                        if external
                        else "filename-id-mismatch",
                        f"record filename {path.name} does not match canonical ID {record_id}",
                    )
                )
            if record_id in records:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        record_id,
                        "duplicate-external-id" if external else "duplicate-id",
                        f"multiple repository records resolve to ID {record_id}",
                    )
                )
                continue
            records[record_id] = model

        return records, findings

    def _artifact_source_findings(
        self, evidence: Evidence
    ) -> list[ClaimEvidenceAuditFinding]:
        findings: list[ClaimEvidenceAuditFinding] = []
        for source in evidence.sources:
            try:
                self.artifact_registry.load(source.artifact_id)
            except (ArtifactNotFoundError, ValidationError, ValueError) as exc:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        evidence.evidence_id,
                        "missing-artifact-source",
                        f"Evidence source Artifact is unavailable or invalid: "
                        f"{source.artifact_id} ({exc})",
                    )
                )
        return findings

    @staticmethod
    def _subject_key(decision: Decision) -> tuple[DecisionSubjectType, str]:
        return decision.subject_type, decision.subject_id

    def _dependency_cycle_findings(
        self, claims: dict[str, Claim]
    ) -> list[ClaimEvidenceAuditFinding]:
        findings: list[ClaimEvidenceAuditFinding] = []
        reported: set[tuple[str, ...]] = set()
        state: dict[str, int] = {}
        stack: list[str] = []

        def visit(claim_id: str) -> None:
            state[claim_id] = 1
            stack.append(claim_id)
            claim = claims[claim_id]
            for dependency_id in claim.depends_on_claim_ids:
                if dependency_id not in claims:
                    continue
                dependency_state = state.get(dependency_id, 0)
                if dependency_state == 0:
                    visit(dependency_id)
                elif dependency_state == 1:
                    start = stack.index(dependency_id)
                    cycle = stack[start:] + [dependency_id]
                    members = tuple(sorted(set(cycle)))
                    if members not in reported:
                        reported.add(members)
                        message = "Claim dependency cycle detected: " + " -> ".join(cycle)
                        for member in members:
                            findings.append(
                                ClaimEvidenceAuditFinding(
                                    member,
                                    "claim-dependency-cycle",
                                    message,
                                )
                            )
            stack.pop()
            state[claim_id] = 2

        for claim_id in sorted(claims):
            if state.get(claim_id, 0) == 0:
                visit(claim_id)

        return findings

    def _decision_history_findings(
        self,
        decisions: dict[str, Decision],
        governed: dict[tuple[DecisionSubjectType, str], Claim | ClaimEvidenceLink],
    ) -> list[ClaimEvidenceAuditFinding]:
        findings: list[ClaimEvidenceAuditFinding] = []
        decisions_by_subject: dict[
            tuple[DecisionSubjectType, str], list[Decision]
        ] = defaultdict(list)

        for decision in decisions.values():
            if decision.subject_type in _PHASE3_SUBJECT_TYPES:
                decisions_by_subject[self._subject_key(decision)].append(decision)

        for subject_key, subject in governed.items():
            subject_id = subject_key[1]
            subject_decisions = decisions_by_subject.get(subject_key, [])
            is_ungoverned = (
                isinstance(subject, Claim)
                and subject.status is ClaimStatus.CANDIDATE
            ) or (
                isinstance(subject, ClaimEvidenceLink)
                and subject.status is RelationStatus.PROPOSED
            )
            if is_ungoverned:
                if subject_decisions:
                    findings.append(
                        ClaimEvidenceAuditFinding(
                            subject_id,
                            "decision-on-ungoverned-state",
                            "candidate/proposed object has Decision records but no canonical governed transition",
                        )
                    )
                continue

            governing_id = subject.governing_decision_id
            if governing_id not in decisions:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        subject_id,
                        "missing-governing-decision",
                        f"governing Decision is unavailable: {governing_id}",
                    )
                )
                continue

            governing = decisions[governing_id]
            if self._subject_key(governing) != subject_key:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        subject_id,
                        "decision-subject-mismatch",
                        f"governing Decision {governing_id} points to "
                        f"{governing.subject_type.value}:{governing.subject_id}",
                    )
                )
            expected = (
                _CLAIM_EXPECTED_STATUS[governing.outcome]
                if isinstance(subject, Claim)
                else _LINK_EXPECTED_STATUS[governing.outcome]
            )
            if subject.status is not expected:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        subject_id,
                        "decision-outcome-mismatch",
                        f"status {subject.status.value} does not match governing "
                        f"Decision outcome {governing.outcome.value}",
                    )
                )

        for subject_key, subject_decisions in decisions_by_subject.items():
            group_ids = {decision.decision_id for decision in subject_decisions}
            children: dict[str, list[str]] = defaultdict(list)
            valid_previous: set[str] = set()

            for decision in subject_decisions:
                previous_id = decision.previous_decision_id
                if previous_id is None:
                    continue
                previous = decisions.get(previous_id)
                if previous is None:
                    findings.append(
                        ClaimEvidenceAuditFinding(
                            decision.decision_id,
                            "missing-previous-decision",
                            f"previous Decision is unavailable: {previous_id}",
                        )
                    )
                    continue
                if self._subject_key(previous) != subject_key:
                    findings.append(
                        ClaimEvidenceAuditFinding(
                            decision.decision_id,
                            "previous-decision-subject-mismatch",
                            f"previous Decision {previous_id} governs a different subject",
                        )
                    )
                    continue
                if previous.decided_at >= decision.decided_at:
                    findings.append(
                        ClaimEvidenceAuditFinding(
                            decision.decision_id,
                            "decision-time-order",
                            f"Decision {decision.decision_id} must occur after {previous_id}",
                        )
                    )
                children[previous_id].append(decision.decision_id)
                valid_previous.add(previous_id)

            for previous_id, child_ids in children.items():
                if len(child_ids) > 1:
                    findings.append(
                        ClaimEvidenceAuditFinding(
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
                            ClaimEvidenceAuditFinding(
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
                    ClaimEvidenceAuditFinding(
                        subject_key[1],
                        "decision-history-roots",
                        "Decision history must have exactly one root when multiple decisions exist",
                    )
                )

            heads = sorted(group_ids - {p for p in valid_previous if p in group_ids})
            if len(heads) != 1:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        subject_key[1],
                        "decision-history-heads",
                        "Decision history must have exactly one current head; found: "
                        + ", ".join(heads),
                    )
                )
                continue

            subject = governed.get(subject_key)
            if subject is not None:
                is_governed = (
                    isinstance(subject, Claim)
                    and subject.status is not ClaimStatus.CANDIDATE
                ) or (
                    isinstance(subject, ClaimEvidenceLink)
                    and subject.status is not RelationStatus.PROPOSED
                )
                if is_governed and subject.governing_decision_id != heads[0]:
                    findings.append(
                        ClaimEvidenceAuditFinding(
                            subject_key[1],
                            "stale-governing-decision",
                            f"governing_decision_id must reference Decision-history head {heads[0]}",
                        )
                    )

        return findings

    def audit(self) -> list[ClaimEvidenceAuditFinding]:
        """Resolve repository-level Claim/Evidence graph references without mutating state."""

        claims, findings = self._audit_collection(self.claims_dir, Claim)
        evidence, evidence_findings = self._audit_collection(self.evidence_dir, Evidence)
        links, link_findings = self._audit_collection(self.links_dir, ClaimEvidenceLink)
        questions, question_findings = self._audit_collection(
            self.questions_dir, ResearchQuestion, external=True
        )
        hypotheses, hypothesis_findings = self._audit_collection(
            self.hypotheses_dir, Hypothesis, external=True
        )
        decisions, decision_findings = self._audit_collection(
            self.decisions_dir, Decision, external=True
        )
        findings.extend(evidence_findings)
        findings.extend(link_findings)
        findings.extend(question_findings)
        findings.extend(hypothesis_findings)
        findings.extend(decision_findings)

        for claim in claims.values():
            question = questions.get(claim.research_question_id)
            if question is None:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        claim.claim_id,
                        "missing-research-question",
                        f"Claim references unavailable ResearchQuestion: "
                        f"{claim.research_question_id}",
                    )
                )

            if claim.hypothesis_id is not None:
                hypothesis = hypotheses.get(claim.hypothesis_id)
                if hypothesis is None:
                    findings.append(
                        ClaimEvidenceAuditFinding(
                            claim.claim_id,
                            "missing-hypothesis",
                            f"Claim references unavailable Hypothesis: {claim.hypothesis_id}",
                        )
                    )
                elif hypothesis.research_question_id != claim.research_question_id:
                    findings.append(
                        ClaimEvidenceAuditFinding(
                            claim.claim_id,
                            "claim-hypothesis-question-mismatch",
                            f"Hypothesis {claim.hypothesis_id} belongs to "
                            f"{hypothesis.research_question_id}, not "
                            f"{claim.research_question_id}",
                        )
                    )

            for dependency_id in claim.depends_on_claim_ids:
                if dependency_id not in claims:
                    findings.append(
                        ClaimEvidenceAuditFinding(
                            claim.claim_id,
                            "missing-claim-dependency",
                            f"dependent Claim is unavailable: {dependency_id}",
                        )
                    )

        findings.extend(self._dependency_cycle_findings(claims))

        for item in evidence.values():
            findings.extend(self._artifact_source_findings(item))

        links_by_claim: dict[str, list[ClaimEvidenceLink]] = defaultdict(list)
        linked_evidence_ids: set[str] = set()
        for link in links.values():
            if link.claim_id not in claims:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        link.link_id,
                        "missing-link-claim",
                        f"ClaimEvidenceLink references unavailable Claim: {link.claim_id}",
                    )
                )
            if link.evidence_id not in evidence:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        link.link_id,
                        "missing-link-evidence",
                        f"ClaimEvidenceLink references unavailable Evidence: {link.evidence_id}",
                    )
                )
            links_by_claim[link.claim_id].append(link)
            linked_evidence_ids.add(link.evidence_id)

        for item in evidence.values():
            if item.evidence_id not in linked_evidence_ids:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        item.evidence_id,
                        "orphan-evidence",
                        "Evidence is not referenced by any ClaimEvidenceLink",
                        GraphAuditSeverity.WARNING,
                    )
                )

        for claim in claims.values():
            accepted_links = [
                link
                for link in links_by_claim.get(claim.claim_id, [])
                if link.status is RelationStatus.ACCEPTED
            ]
            accepted_support = [
                link
                for link in accepted_links
                if link.relation is EvidenceRelation.SUPPORTS
                and link.evidence_id in evidence
            ]
            accepted_contradictions = [
                link
                for link in accepted_links
                if link.relation is EvidenceRelation.CONTRADICTS
                and link.evidence_id in evidence
            ]

            if claim.status is ClaimStatus.APPROVED and not accepted_support:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        claim.claim_id,
                        "approved-claim-without-accepted-support",
                        "approved Claim has no accepted supporting ClaimEvidenceLink "
                        "to available Evidence",
                        GraphAuditSeverity.WARNING,
                    )
                )

            if accepted_support and accepted_contradictions:
                support_ids = ", ".join(sorted(link.link_id for link in accepted_support))
                contradiction_ids = ", ".join(
                    sorted(link.link_id for link in accepted_contradictions)
                )
                findings.append(
                    ClaimEvidenceAuditFinding(
                        claim.claim_id,
                        "accepted-evidence-conflict",
                        "Claim has accepted supporting and contradicting evidence links; "
                        f"supports=[{support_ids}], contradicts=[{contradiction_ids}]",
                        GraphAuditSeverity.WARNING,
                    )
                )

        governed: dict[
            tuple[DecisionSubjectType, str], Claim | ClaimEvidenceLink
        ] = {
            (DecisionSubjectType.CLAIM, claim.claim_id): claim
            for claim in claims.values()
        }
        governed.update(
            {
                (DecisionSubjectType.CLAIM_EVIDENCE_LINK, link.link_id): link
                for link in links.values()
            }
        )

        for decision in decisions.values():
            if decision.subject_type is DecisionSubjectType.CLAIM:
                subject_exists = decision.subject_id in claims
            elif decision.subject_type is DecisionSubjectType.CLAIM_EVIDENCE_LINK:
                subject_exists = decision.subject_id in links
            else:
                continue
            if not subject_exists:
                findings.append(
                    ClaimEvidenceAuditFinding(
                        decision.decision_id,
                        "missing-decision-subject",
                        f"Decision subject is unavailable: {decision.subject_id}",
                    )
                )

        findings.extend(self._decision_history_findings(decisions, governed))

        return sorted(
            findings,
            key=lambda item: (
                item.severity.value,
                item.record_id,
                item.code,
                item.message,
            ),
        )
