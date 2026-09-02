from __future__ import annotations

import re

_CLAIM_ID_RE = re.compile(r"^clm-[a-z0-9][a-z0-9._-]{2,63}$")
_EVIDENCE_ID_RE = re.compile(r"^ev-[a-z0-9][a-z0-9._-]{2,63}$")
_CLAIM_EVIDENCE_LINK_ID_RE = re.compile(r"^cel-[a-z0-9][a-z0-9._-]{2,63}$")
_CITATION_ID_RE = re.compile(r"^cit-[a-z0-9][a-z0-9._-]{2,63}$")
_LITERATURE_NOTE_ID_RE = re.compile(r"^litn-[a-z0-9][a-z0-9._-]{2,63}$")
_EXPERIMENT_ID_RE = re.compile(r"^exp-[a-z0-9][a-z0-9._-]{2,63}$")
_EXPERIMENT_RUN_ID_RE = re.compile(r"^exprun-[a-z0-9][a-z0-9._-]{2,63}$")


def validate_claim_id(value: str) -> str:
    if not _CLAIM_ID_RE.fullmatch(value):
        raise ValueError(
            "claim IDs must match 'clm-' followed by 3-64 lowercase slug characters"
        )
    return value


def validate_evidence_id(value: str) -> str:
    if not _EVIDENCE_ID_RE.fullmatch(value):
        raise ValueError(
            "evidence IDs must match 'ev-' followed by 3-64 lowercase slug characters"
        )
    return value


def validate_claim_evidence_link_id(value: str) -> str:
    if not _CLAIM_EVIDENCE_LINK_ID_RE.fullmatch(value):
        raise ValueError(
            "claim-evidence link IDs must match 'cel-' followed by 3-64 lowercase slug characters"
        )
    return value


def validate_citation_id(value: str) -> str:
    if not _CITATION_ID_RE.fullmatch(value):
        raise ValueError(
            "citation IDs must match 'cit-' followed by 3-64 lowercase slug characters"
        )
    return value


def validate_literature_note_id(value: str) -> str:
    if not _LITERATURE_NOTE_ID_RE.fullmatch(value):
        raise ValueError(
            "literature note IDs must match 'litn-' followed by 3-64 lowercase slug characters"
        )
    return value


def validate_experiment_id(value: str) -> str:
    if not _EXPERIMENT_ID_RE.fullmatch(value):
        raise ValueError(
            "experiment IDs must match 'exp-' followed by 3-64 lowercase slug characters"
        )
    return value


def validate_experiment_run_id(value: str) -> str:
    if not _EXPERIMENT_RUN_ID_RE.fullmatch(value):
        raise ValueError(
            "experiment run IDs must match 'exprun-' followed by 3-64 lowercase slug characters"
        )
    return value
