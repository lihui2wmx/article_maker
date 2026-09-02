from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .claim_evidence import Evidence, EvidenceKind, EvidenceSourceRef
from .claim_registry import (
    ClaimEvidenceNotFoundError,
    ClaimEvidenceRegistry,
    GraphAuditSeverity,
)
from .literature import (
    Citation,
    LiteratureNote,
    LiteratureNoteItem,
    LiteratureStatementType,
)
from .literature_registry import LiteratureNotFoundError, LiteratureRegistry
from .registration import ArtifactNotFoundError


class LiteratureEvidenceBridgeError(RuntimeError):
    """Base error for literature-to-Evidence proposal and execution."""


class LiteratureEvidenceEligibilityError(LiteratureEvidenceBridgeError):
    """Raised when selected literature content is not eligible for Evidence promotion."""


class LiteratureEvidencePlanError(LiteratureEvidenceBridgeError):
    """Raised when a proposal plan is internally invalid or ambiguous."""


class LiteratureEvidenceApprovalError(LiteratureEvidenceBridgeError):
    """Raised when execution is not bound to the reviewed plan digest."""


class LiteratureEvidenceStaleError(LiteratureEvidenceBridgeError):
    """Raised when literature records changed after proposal review."""


class LiteratureEvidenceConflictError(LiteratureEvidenceBridgeError):
    """Raised when a planned Evidence identity is already occupied."""


class LiteratureEvidencePostWriteError(LiteratureEvidenceBridgeError):
    """Raised when persisted Evidence differs from the reviewed preview or fails audit."""


@dataclass(frozen=True, slots=True)
class LiteratureEvidenceSelection:
    literature_note_id: str
    item_index: int


@dataclass(frozen=True, slots=True)
class PlannedLiteratureEvidence:
    literature_note_id: str
    citation_id: str
    item_index: int
    citation_digest: str
    note_digest: str
    evidence: Evidence


@dataclass(frozen=True, slots=True)
class LiteratureEvidencePlan:
    entries: tuple[PlannedLiteratureEvidence, ...]


@dataclass(frozen=True, slots=True)
class LiteratureEvidenceExecutionResult:
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


def _item_digest(item: LiteratureNoteItem) -> str:
    return _model_digest(item)


def generated_literature_evidence_id(
    citation: Citation,
    note: LiteratureNote,
    item: LiteratureNoteItem,
) -> str:
    payload = {
        "bridge_version": "1",
        "citation_id": citation.citation_id,
        "literature_note_id": note.literature_note_id,
        "item": item.model_dump(mode="json"),
    }
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return f"ev-lit-{hashlib.sha256(serialized).hexdigest()[:24]}"


def _preview_evidence(
    citation: Citation,
    note: LiteratureNote,
    item_index: int,
) -> Evidence:
    try:
        item = note.items[item_index]
    except IndexError as exc:
        raise LiteratureEvidenceEligibilityError(
            f"literature note item index is out of range: {item_index}"
        ) from exc

    if item.statement_type is not LiteratureStatementType.SOURCE_REPORT:
        raise LiteratureEvidenceEligibilityError(
            "only source_report LiteratureNote items may become literature Evidence"
        )

    citation_artifacts = set(citation.source_artifact_ids)
    if any(ref.artifact_id not in citation_artifacts for ref in item.source_refs):
        raise LiteratureEvidenceEligibilityError(
            "source_report provenance must remain within the referenced Citation provenance"
        )

    evidence_id = generated_literature_evidence_id(citation, note, item)
    return Evidence(
        schema_version="1.0",
        evidence_id=evidence_id,
        kind=EvidenceKind.LITERATURE_STATEMENT,
        description=item.text,
        recorded_by=note.recorded_by,
        sources=[
            EvidenceSourceRef(
                artifact_id=ref.artifact_id,
                locator=ref.locator,
            )
            for ref in item.source_refs
        ],
        metadata={
            "literature_bridge": {
                "citation_id": citation.citation_id,
                "literature_note_id": note.literature_note_id,
                "item_index": item_index,
                "item_kind": item.kind.value,
                "statement_type": item.statement_type.value,
                "item_digest": _item_digest(item),
            }
        },
    )


def literature_evidence_plan_digest(plan: LiteratureEvidencePlan) -> str:
    payload = [
        {
            "literature_note_id": entry.literature_note_id,
            "citation_id": entry.citation_id,
            "item_index": entry.item_index,
            "citation_digest": entry.citation_digest,
            "note_digest": entry.note_digest,
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


class LiteratureEvidenceBridge:
    """Plan and execute reviewed promotion of source-reported literature into Evidence."""

    def __init__(self, repository_root: Path | str):
        self.literature_registry = LiteratureRegistry(repository_root)
        self.claim_registry = ClaimEvidenceRegistry(repository_root)
        self.artifact_registry = self.literature_registry.artifact_registry

    def _load_pair(self, literature_note_id: str) -> tuple[Citation, LiteratureNote]:
        try:
            note = self.literature_registry.load_note(literature_note_id)
            citation = self.literature_registry.load_citation(note.citation_id)
        except (LiteratureNotFoundError, ValidationError, ValueError) as exc:
            raise LiteratureEvidenceEligibilityError(
                f"literature source records are unavailable or invalid: {literature_note_id}"
            ) from exc
        return citation, note

    def _validate_artifact_sources(self, evidence: Evidence) -> None:
        for source in evidence.sources:
            try:
                self.artifact_registry.load(source.artifact_id)
            except (ArtifactNotFoundError, ValidationError, ValueError) as exc:
                raise LiteratureEvidenceEligibilityError(
                    f"source Artifact is unavailable or invalid: {source.artifact_id}"
                ) from exc

    def plan(
        self,
        selections: list[LiteratureEvidenceSelection],
    ) -> LiteratureEvidencePlan:
        if not selections:
            raise LiteratureEvidencePlanError("at least one literature Evidence selection is required")

        entries: list[PlannedLiteratureEvidence] = []
        seen_sources: set[tuple[str, int]] = set()
        seen_evidence_ids: set[str] = set()

        for selection in selections:
            if selection.item_index < 0:
                raise LiteratureEvidencePlanError("literature note item_index must be non-negative")
            source_key = (selection.literature_note_id, selection.item_index)
            if source_key in seen_sources:
                raise LiteratureEvidencePlanError(
                    f"duplicate literature Evidence selection: {selection.literature_note_id}[{selection.item_index}]"
                )
            seen_sources.add(source_key)

            citation, note = self._load_pair(selection.literature_note_id)
            evidence = _preview_evidence(citation, note, selection.item_index)
            self._validate_artifact_sources(evidence)

            if evidence.evidence_id in seen_evidence_ids:
                raise LiteratureEvidencePlanError(
                    f"multiple selections resolve to Evidence ID {evidence.evidence_id}"
                )
            seen_evidence_ids.add(evidence.evidence_id)

            try:
                self.claim_registry.load_evidence(evidence.evidence_id)
            except ClaimEvidenceNotFoundError:
                pass
            else:
                raise LiteratureEvidenceConflictError(
                    f"Evidence already exists: {evidence.evidence_id}"
                )

            entries.append(
                PlannedLiteratureEvidence(
                    literature_note_id=note.literature_note_id,
                    citation_id=citation.citation_id,
                    item_index=selection.item_index,
                    citation_digest=_model_digest(citation),
                    note_digest=_model_digest(note),
                    evidence=evidence,
                )
            )

        entries.sort(key=lambda entry: (entry.literature_note_id, entry.item_index))
        return LiteratureEvidencePlan(entries=tuple(entries))

    def execute(
        self,
        plan: LiteratureEvidencePlan,
        *,
        reviewed_digest: str,
    ) -> LiteratureEvidenceExecutionResult:
        snapshot = copy.deepcopy(plan)
        actual_digest = literature_evidence_plan_digest(snapshot)
        if reviewed_digest != actual_digest:
            raise LiteratureEvidenceApprovalError(
                "reviewed_digest does not match the exact literature Evidence plan"
            )

        if not snapshot.entries:
            raise LiteratureEvidencePlanError("cannot execute an empty literature Evidence plan")

        for entry in snapshot.entries:
            citation, note = self._load_pair(entry.literature_note_id)
            if citation.citation_id != entry.citation_id:
                raise LiteratureEvidenceStaleError(
                    f"LiteratureNote now points to a different Citation: {entry.literature_note_id}"
                )
            if _model_digest(citation) != entry.citation_digest:
                raise LiteratureEvidenceStaleError(
                    f"Citation changed after review: {entry.citation_id}"
                )
            if _model_digest(note) != entry.note_digest:
                raise LiteratureEvidenceStaleError(
                    f"LiteratureNote changed after review: {entry.literature_note_id}"
                )

            regenerated = _preview_evidence(citation, note, entry.item_index)
            self._validate_artifact_sources(regenerated)
            if regenerated.model_dump(mode="json") != entry.evidence.model_dump(mode="json"):
                raise LiteratureEvidencePlanError(
                    f"reviewed Evidence preview is not the deterministic projection of "
                    f"{entry.literature_note_id}[{entry.item_index}]"
                )

            try:
                self.claim_registry.load_evidence(entry.evidence.evidence_id)
            except ClaimEvidenceNotFoundError:
                pass
            else:
                raise LiteratureEvidenceConflictError(
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
                    raise LiteratureEvidencePostWriteError(
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
                raise LiteratureEvidencePostWriteError(
                    f"post-write graph audit found structural errors: {summary}"
                )
        except Exception:
            for path in reversed(written_paths):
                path.unlink(missing_ok=True)
            raise

        return LiteratureEvidenceExecutionResult(
            plan_digest=actual_digest,
            evidence_ids=tuple(entry.evidence.evidence_id for entry in snapshot.entries),
        )
