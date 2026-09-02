from __future__ import annotations

import json
import os
import re
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable, TypeVar

from pydantic import BaseModel, ValidationError

from .literature import Citation, LiteratureNote
from .registration import ArtifactNotFoundError, ArtifactRegistry
from .scientific_ids import validate_citation_id, validate_literature_note_id

DEFAULT_LITERATURE_PATH = "literature"


class LiteratureRegistryError(RuntimeError):
    """Base error for filesystem-backed literature persistence."""


class LiteratureNotFoundError(LiteratureRegistryError):
    """Raised when a requested Citation or LiteratureNote is unavailable."""


class LiteratureAuditSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class LiteratureAuditFinding:
    record_id: str
    code: str
    message: str
    severity: LiteratureAuditSeverity = LiteratureAuditSeverity.ERROR


_ModelT = TypeVar("_ModelT", bound=BaseModel)


def _normalized_title(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _issued_year(value: str | None) -> str | None:
    return value[:4] if value else None


class LiteratureRegistry:
    """Persist and audit repository-level Citation and LiteratureNote state."""

    def __init__(
        self,
        repository_root: Path | str,
        *,
        literature_path: str = DEFAULT_LITERATURE_PATH,
    ):
        try:
            self.repository_root = Path(repository_root).resolve(strict=True)
        except OSError as exc:
            raise LiteratureRegistryError(
                "repository_root must be an existing directory"
            ) from exc
        if not self.repository_root.is_dir():
            raise LiteratureRegistryError(
                "repository_root must be an existing directory"
            )

        self.literature_root = self._resolve_repository_directory(literature_path)
        self.metadata_dir = self.literature_root / "metadata"
        self.notes_dir = self.literature_root / "notes"
        self.artifact_registry = ArtifactRegistry(self.repository_root)

    def _resolve_repository_directory(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise LiteratureRegistryError(
                "registry paths must be repository-relative and must not traverse upward"
            )
        resolved = (self.repository_root / candidate).resolve(strict=False)
        try:
            resolved.relative_to(self.repository_root)
        except ValueError as exc:
            raise LiteratureRegistryError(
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

    def save_citation(self, citation: Citation) -> Citation:
        self._write(self.metadata_dir, citation.citation_id, citation)
        return citation

    def save_note(self, note: LiteratureNote) -> LiteratureNote:
        self._write(self.notes_dir, note.literature_note_id, note)
        return note

    @staticmethod
    def _load(path: Path, model_type: type[_ModelT], record_id: str) -> _ModelT:
        if not path.is_file():
            raise LiteratureNotFoundError(f"literature record not found: {record_id}")
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))

    def load_citation(self, citation_id: str) -> Citation:
        validate_citation_id(citation_id)
        return self._load(
            self.metadata_dir / f"{citation_id}.json",
            Citation,
            citation_id,
        )

    def load_note(self, literature_note_id: str) -> LiteratureNote:
        validate_literature_note_id(literature_note_id)
        return self._load(
            self.notes_dir / f"{literature_note_id}.json",
            LiteratureNote,
            literature_note_id,
        )

    @staticmethod
    def _iter_json(directory: Path) -> Iterable[Path]:
        if not directory.exists():
            return ()
        return tuple(sorted(directory.glob("*.json")))

    def list_citations(self) -> list[Citation]:
        return [
            Citation.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self._iter_json(self.metadata_dir)
        ]

    def list_notes(self) -> list[LiteratureNote]:
        return [
            LiteratureNote.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self._iter_json(self.notes_dir)
        ]

    @staticmethod
    def _record_id(model: BaseModel) -> str:
        if isinstance(model, Citation):
            return model.citation_id
        if isinstance(model, LiteratureNote):
            return model.literature_note_id
        raise TypeError(f"unsupported literature model: {type(model)!r}")

    def _audit_collection(
        self,
        directory: Path,
        model_type: type[_ModelT],
    ) -> tuple[dict[str, _ModelT], list[LiteratureAuditFinding]]:
        records: dict[str, _ModelT] = {}
        findings: list[LiteratureAuditFinding] = []

        for path in self._iter_json(directory):
            try:
                model = model_type.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValidationError, ValueError) as exc:
                findings.append(
                    LiteratureAuditFinding(
                        path.stem,
                        "invalid-record",
                        f"record cannot be parsed as {model_type.__name__}: {exc}",
                    )
                )
                continue

            record_id = self._record_id(model)
            if path.stem != record_id:
                findings.append(
                    LiteratureAuditFinding(
                        record_id,
                        "filename-id-mismatch",
                        f"record filename {path.name} does not match canonical ID {record_id}",
                    )
                )
            if record_id in records:
                findings.append(
                    LiteratureAuditFinding(
                        record_id,
                        "duplicate-id",
                        f"multiple repository records resolve to ID {record_id}",
                    )
                )
                continue
            records[record_id] = model

        return records, findings

    def _artifact_exists(self, artifact_id: str) -> bool:
        try:
            self.artifact_registry.load(artifact_id)
        except (ArtifactNotFoundError, ValidationError, ValueError):
            return False
        return True

    @staticmethod
    def _identifier_collisions(
        citations: dict[str, Citation],
    ) -> list[LiteratureAuditFinding]:
        findings: list[LiteratureAuditFinding] = []
        owners: dict[tuple[str, str], list[str]] = defaultdict(list)

        for citation in citations.values():
            for identifier in citation.identifiers:
                owners[(identifier.scheme.value, identifier.value.casefold())].append(
                    citation.citation_id
                )

        for (scheme, value), citation_ids in sorted(owners.items()):
            unique_ids = sorted(set(citation_ids))
            if len(unique_ids) < 2:
                continue
            message = (
                f"external identifier {scheme}:{value} appears on multiple Citations: "
                + ", ".join(unique_ids)
            )
            for citation_id in unique_ids:
                findings.append(
                    LiteratureAuditFinding(
                        citation_id,
                        "external-identifier-collision",
                        message,
                        LiteratureAuditSeverity.WARNING,
                    )
                )

        return findings

    @staticmethod
    def _preferred_key_collisions(
        citations: dict[str, Citation],
    ) -> list[LiteratureAuditFinding]:
        findings: list[LiteratureAuditFinding] = []
        owners: dict[str, list[str]] = defaultdict(list)

        for citation in citations.values():
            if citation.preferred_key is not None:
                owners[citation.preferred_key.casefold()].append(citation.citation_id)

        for key, citation_ids in sorted(owners.items()):
            unique_ids = sorted(set(citation_ids))
            if len(unique_ids) < 2:
                continue
            message = (
                f"preferred citation key {key!r} is ambiguous across Citations: "
                + ", ".join(unique_ids)
            )
            for citation_id in unique_ids:
                findings.append(
                    LiteratureAuditFinding(
                        citation_id,
                        "preferred-key-collision",
                        message,
                    )
                )

        return findings

    @staticmethod
    def _possible_duplicate_work_findings(
        citations: dict[str, Citation],
    ) -> list[LiteratureAuditFinding]:
        findings: list[LiteratureAuditFinding] = []
        groups: dict[tuple[str, str | None], list[str]] = defaultdict(list)

        for citation in citations.values():
            groups[
                (_normalized_title(citation.title), _issued_year(citation.issued))
            ].append(citation.citation_id)

        for (title, year), citation_ids in sorted(groups.items()):
            unique_ids = sorted(set(citation_ids))
            if len(unique_ids) < 2:
                continue
            message = (
                f"multiple Citations share normalized title/year {title!r}/{year or 'unknown'}: "
                + ", ".join(unique_ids)
            )
            for citation_id in unique_ids:
                findings.append(
                    LiteratureAuditFinding(
                        citation_id,
                        "possible-duplicate-work",
                        message,
                        LiteratureAuditSeverity.WARNING,
                    )
                )

        return findings

    def audit(self) -> list[LiteratureAuditFinding]:
        """Audit literature persistence and cross-record integrity without mutation."""

        citations, findings = self._audit_collection(self.metadata_dir, Citation)
        notes, note_findings = self._audit_collection(self.notes_dir, LiteratureNote)
        findings.extend(note_findings)

        for citation in citations.values():
            for artifact_id in citation.source_artifact_ids:
                if not self._artifact_exists(artifact_id):
                    findings.append(
                        LiteratureAuditFinding(
                            citation.citation_id,
                            "missing-citation-artifact",
                            f"Citation source Artifact is unavailable or invalid: {artifact_id}",
                        )
                    )

        for note in notes.values():
            citation = citations.get(note.citation_id)
            if citation is None:
                findings.append(
                    LiteratureAuditFinding(
                        note.literature_note_id,
                        "missing-note-citation",
                        f"LiteratureNote references unavailable Citation: {note.citation_id}",
                    )
                )

            citation_artifacts = (
                set(citation.source_artifact_ids) if citation is not None else set()
            )
            for item_index, item in enumerate(note.items):
                for source_ref in item.source_refs:
                    if not self._artifact_exists(source_ref.artifact_id):
                        findings.append(
                            LiteratureAuditFinding(
                                note.literature_note_id,
                                "missing-note-artifact",
                                f"note item {item_index} source Artifact is unavailable or invalid: "
                                f"{source_ref.artifact_id}",
                            )
                        )
                    if citation is not None and source_ref.artifact_id not in citation_artifacts:
                        findings.append(
                            LiteratureAuditFinding(
                                note.literature_note_id,
                                "note-artifact-outside-citation-provenance",
                                f"note item {item_index} uses Artifact {source_ref.artifact_id} "
                                f"outside Citation {citation.citation_id} provenance",
                            )
                        )

        findings.extend(self._preferred_key_collisions(citations))
        findings.extend(self._identifier_collisions(citations))
        findings.extend(self._possible_duplicate_work_findings(citations))

        return sorted(
            findings,
            key=lambda item: (
                item.severity.value,
                item.record_id,
                item.code,
                item.message,
            ),
        )
