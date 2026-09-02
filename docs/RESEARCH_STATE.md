# Research State Contracts

Phase 2 begins the transition from artifact management to explicit scientific project state.

Phase 2A defines three canonical object contracts:

- `ResearchQuestion`
- `Hypothesis`
- `Decision`

The contracts are intentionally small. They describe what the project is considering and which human decisions govern its current state. They do **not** yet represent claims, evidence, experiments, literature interpretation, or agent reasoning traces.

## Canonical contract

`schemas/research-state.schema.json` is the framework-neutral JSON Schema Draft 2020-12 contract. The Pydantic models in `src/article_maker/research_state.py` are the Python implementation.

Repository state must not depend on Pydantic internals or a particular agent framework.

## ResearchQuestion

A research question contains:

- a stable `rq-*` identifier;
- the question text;
- lifecycle status;
- proposal attribution;
- an optional governing human decision reference;
- optional artifact references;
- JSON metadata for low-risk extension data.

Example:

```json
{
  "schema_version": "1.0",
  "research_question_id": "rq-interface-stability",
  "question": "How does interface regularization affect solver robustness?",
  "status": "proposed",
  "proposed_by": {
    "source": "agent",
    "actor": "planner-agent"
  },
  "governing_decision_id": null,
  "artifact_refs": ["art-note-background"],
  "metadata": {}
}
```

## Hypothesis

A hypothesis contains:

- a stable `hyp-*` identifier;
- exactly one `research_question_id` reference;
- a testable/analyzable proposition;
- the same governed lifecycle mechanism as a research question;
- optional artifact references and JSON metadata.

Phase 2A validates the syntax of `research_question_id`. It does not yet resolve that reference against repository state.

## Lifecycle states

Research questions and hypotheses use four states:

| State | Meaning | Governing Decision |
| --- | --- | --- |
| `proposed` | Candidate state, not approved as project direction | forbidden |
| `accepted` | Accepted into canonical research direction | required |
| `rejected` | Explicitly declined | required |
| `superseded` | Replaced/retired by a later human decision | required |

A proposal may originate from a human or an agent. Proposal attribution therefore has `source = human | agent`.

Proposal authority is deliberately different from approval authority.

## Decision

A `Decision` is the human-governance record that authorizes a non-proposed research-state status.

It contains:

- stable `dec-*` identity;
- subject type and subject ID;
- outcome (`approve`, `reject`, `supersede`);
- `authority`, fixed to `human` in schema version 1.0;
- a non-blank `decided_by` label;
- a timezone-aware `decided_at` timestamp;
- required rationale;
- optional artifact references and JSON metadata.

Outcome maps to lifecycle state as follows:

| Decision outcome | Governed object status |
| --- | --- |
| `approve` | `accepted` |
| `reject` | `rejected` |
| `supersede` | `superseded` |

The schema does not authenticate the person named by `decided_by`. It records declared authority and provenance. Authentication/identity integration, if needed, is a separate infrastructure concern.

## Why approval is a separate object

Scientific approval must not be represented as an editable boolean such as:

```text
approved: true
```

A separate Decision gives the repository an inspectable record of:

- what object was governed;
- what outcome was chosen;
- who declared the decision;
- when it occurred;
- why it was chosen;
- which artifacts informed it.

This makes later review and Git history materially more informative.

## Artifact references

`artifact_refs` reuse the Phase 1 `art-*` grammar.

Phase 2A checks only syntax and duplicate references. It does not require referenced manifests to exist. Reference resolution belongs to the repository-level research-state registry/audit layer planned for Phase 2B.

## Object-level versus repository-level validation

Phase 2A can prove local invariants such as:

- IDs follow the correct grammar;
- a proposed object has no governing decision;
- a non-proposed object has a decision reference;
- a Decision has human authority;
- Decision subject type matches subject ID grammar;
- timestamps are timezone-aware;
- artifact references are syntactically valid and unique.

It cannot yet prove cross-object invariants such as:

- the referenced Decision exists;
- the Decision points back to the same ResearchQuestion/Hypothesis;
- the Decision outcome matches the object's current status;
- the referenced ResearchQuestion exists for a Hypothesis;
- referenced artifact manifests exist;
- multiple conflicting Decisions are absent.

Those checks require repository-level resolution and are intentionally deferred to Phase 2B rather than hidden inside object constructors.

## Human authority boundary

Agents may:

- propose a ResearchQuestion;
- propose a Hypothesis;
- attach relevant artifact references;
- recommend an approval/rejection decision;
- explain tradeoffs.

Agents may not create a canonical non-human approval authority under schema version 1.0. A ResearchQuestion or Hypothesis becomes accepted canonical direction only through a human Decision record and subsequent repository-level consistency validation.

## Non-goals

Phase 2A does not introduce:

- Claim or Evidence objects;
- claim approval;
- experiment orchestration;
- literature extraction;
- semantic parsing;
- LLM providers;
- agent runtime/orchestration;
- automatic research-direction approval;
- external identity/authentication systems;
- a research-state persistence registry.
