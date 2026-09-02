# Artifact Manifest Contract v1.0

## Purpose

An `ArtifactManifest` is the smallest durable record that lets `article_maker` identify a research artifact, locate it in the repository, classify its role, and trace how it was produced.

The manifest is deliberately **not** a paper parser, experiment schema, citation record, claim record, or vector-index entry. Those objects will reference artifacts rather than overloading this contract.

The language-independent contract is `schemas/artifact-manifest.schema.json`. The Pydantic model in `src/article_maker/artifacts.py` is the initial Python validator and may enforce semantic invariants that JSON Schema cannot express directly.

## Required fields

| Field | Meaning |
|---|---|
| `schema_version` | Contract version. Phase 1A supports exactly `1.0`. |
| `artifact_id` | Stable repository identifier matching `art-[a-z0-9][a-z0-9._-]{2,63}`. It is independent of the file name. |
| `kind` | Coarse artifact category used for routing and later ingestion. |
| `stage` | `source` for lineage roots, `derived` for artifacts produced from other registered artifacts. |
| `path` | Normalized repository-relative POSIX path to the artifact. |
| `media_type` | MIME-style media type such as `application/pdf`, `text/markdown`, or `inode/directory`. |
| `provenance` | Minimal producer and parent lineage information. |

Optional fields provide display text, SHA-256 integrity, tags, and non-canonical metadata.

## Artifact kinds

Version 1.0 defines these coarse kinds:

- `paper`
- `note`
- `slide_deck`
- `source_code`
- `dataset`
- `experiment_config`
- `experiment_output`
- `figure`
- `table`
- `manuscript_source`
- `bibliography`
- `supplementary`
- `model_output`
- `other`

The list is intentionally coarse. Domain-specific meaning belongs in later typed objects instead of continuously expanding artifact kinds.

## Source and derived semantics

`stage` describes lineage, not scientific validity.

A **source artifact** is a lineage root inside the project and therefore has:

```json
{
  "stage": "source",
  "provenance": {
    "producer": "external",
    "parent_artifacts": []
  }
}
```

Examples include an imported reference PDF, a researcher-created raw note, or a newly added dataset whose upstream history is outside this repository.

A **derived artifact** is produced from one or more registered artifacts and therefore must list at least one parent:

```json
{
  "stage": "derived",
  "provenance": {
    "producer": "experiment",
    "parent_artifacts": [
      "art-exp001-config",
      "art-exp001-code"
    ]
  }
}
```

Examples include experiment outputs, generated figures, converted text, AI-generated summaries, and manuscript fragments generated from registered inputs.

A derived artifact without parents is invalid because it breaks provenance. A source artifact with parents is invalid because it is not a lineage root.

## Producer types

`provenance.producer` records the immediate producer class:

- `external`: imported material created outside this project;
- `human`: directly created by a researcher;
- `experiment`: produced by an experiment workflow;
- `tool`: produced by a deterministic or non-agent software tool;
- `agent`: produced by an AI agent.

This field records provenance only. It does not imply trust, approval, or scientific validity.

## Path rules

Artifact paths must:

- be relative to repository root;
- use `/` separators;
- be normalized;
- not start with `/` or `./`;
- not contain `.` or `..` path segments;
- not contain repeated separators.

Valid:

```text
literature/sources/smith-2025.pdf
experiments/exp001/results/metrics.json
code/solver/
```

Invalid:

```text
/home/user/paper.pdf
../outside/data.csv
./notes/a.md
literature//paper.pdf
C:\research\paper.pdf
```

The contract allows both files and directories. Directory artifacts should use an appropriate media type such as `inode/directory`.

## Integrity and Git provenance

`checksum_sha256`, when present, is the lowercase SHA-256 digest of the artifact bytes. Phase 1B ingestion is expected to compute it automatically for regular files.

`provenance.git_revision` may record the Git revision associated with generation. It is intentionally optional because imported source material may predate repository tracking and because not every artifact is generated from code.

`command` and `tool` are optional execution hints. They are not substitutes for a future typed experiment record.

## Metadata boundary

`metadata` is an extensibility escape hatch for low-criticality JSON metadata. It must not become a shadow schema.

Scientific state with durable semantics—authors, bibliographic identity, experiment parameters, claims, evidence relations, approval state, statistical results, journal constraints—must move into dedicated typed domain objects in the appropriate phase.

## Semantic invariants

The Python validator additionally enforces:

1. artifact IDs and parent IDs follow the same stable ID format;
2. parent IDs are unique;
3. an artifact cannot list itself as a parent;
4. source artifacts have zero parents;
5. derived artifacts have at least one parent;
6. optional text fields cannot be blank;
7. checksums and Git revisions use normalized lowercase hexadecimal form;
8. unknown top-level and provenance fields are rejected.

## Complete source example

```json
{
  "schema_version": "1.0",
  "artifact_id": "art-smith-2025-paper",
  "kind": "paper",
  "stage": "source",
  "path": "literature/sources/smith-2025.pdf",
  "media_type": "application/pdf",
  "title": "Example Reference Paper",
  "checksum_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "tags": ["reference", "numerical-methods"],
  "provenance": {
    "producer": "external",
    "parent_artifacts": []
  },
  "metadata": {}
}
```

## Complete derived example

```json
{
  "schema_version": "1.0",
  "artifact_id": "art-exp001-figure-convergence",
  "kind": "figure",
  "stage": "derived",
  "path": "experiments/exp001/figures/convergence.pdf",
  "media_type": "application/pdf",
  "tags": ["experiment", "convergence"],
  "provenance": {
    "producer": "experiment",
    "parent_artifacts": [
      "art-exp001-config",
      "art-exp001-code"
    ],
    "git_revision": "5b46db1",
    "command": "python experiments/exp001/run.py",
    "tool": "python"
  },
  "metadata": {}
}
```

## Versioning rule

Consumers must reject unsupported `schema_version` values rather than guessing migrations. A future incompatible manifest format will receive a new explicit version and migration path.
