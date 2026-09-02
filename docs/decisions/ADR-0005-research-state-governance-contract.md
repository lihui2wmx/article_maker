# ADR-0005: Research-state governance contract

- **Status:** Accepted for Phase 2A
- **Date:** 2026-09-02

## Context

Phase 1 made repository artifacts traceable and reviewable, but the project still lacks canonical representation of research direction.

The next layer must represent research questions, hypotheses, and human decisions without creating a back door through which agents can silently approve scientific direction.

A naive design could place fields such as `approved: true` or `status: accepted` directly on a proposal without recording the authority and rationale for that transition. That would make scientific governance easy to mutate and difficult to audit.

## Decision

### 1. Use a framework-neutral schema bundle

`schemas/research-state.schema.json` is the canonical cross-language contract for `ResearchQuestion`, `Hypothesis`, and `Decision`.

Python/Pydantic models are an implementation, not the source of truth.

### 2. Separate proposal attribution from approval authority

Research questions and hypotheses may be proposed by either:

- a human;
- an agent.

Proposal attribution does not grant approval authority.

### 3. Model approval/rejection/supersession as explicit Decision records

ResearchQuestion and Hypothesis lifecycle states are:

- `proposed`;
- `accepted`;
- `rejected`;
- `superseded`.

`proposed` objects must not have a governing Decision.

Every non-proposed state must reference a `governing_decision_id`.

### 4. Fix Decision authority to human in schema version 1.0

`Decision.authority` is a schema constant equal to `human`.

Agents may recommend or draft a decision but cannot represent themselves as canonical approval authority.

### 5. Keep Decision outcome semantically minimal

Decision outcomes are:

- `approve` -> governed status `accepted`;
- `reject` -> governed status `rejected`;
- `supersede` -> governed status `superseded`.

The Decision records rationale and a timezone-aware timestamp.

### 6. Reuse Artifact IDs for supporting references

Research-state objects may reference Phase 1 artifacts using `art-*` IDs.

Phase 2A validates only ID syntax and duplicate references.

### 7. Defer cross-object resolution to Phase 2B

Object constructors and JSON Schema cannot establish repository-level truth about referenced files.

Phase 2B must resolve and audit at least:

- Hypothesis -> ResearchQuestion existence;
- governed object -> Decision existence;
- Decision -> subject backlink consistency;
- Decision outcome -> current lifecycle status consistency;
- research-state object -> Artifact existence;
- conflicting governance records.

## Consequences

### Positive

- Human authority is visible in canonical state rather than implied by mutable booleans.
- Agent proposals are first-class without being confused with approval.
- Governance changes are reviewable in Git history.
- Research-state contracts remain independent of LLM providers and agent frameworks.
- The later Claim/Evidence graph can attach to stable research-direction objects.

### Costs

- A valid standalone object is not sufficient to prove repository-level governance consistency.
- State transitions require creation of a Decision plus update of the governed object.
- Phase 2B needs explicit cross-object resolution/audit rather than relying only on schema validation.

## Rejected alternatives

### Boolean approval fields

Rejected because they erase authority, rationale, and decision provenance.

### Allow agent authority with a role field

Rejected for v1 because it contradicts the project's human scientific authority gate.

### Put all reasoning into Decision metadata

Rejected because rationale is core governance state and must remain a required typed field.

### Resolve repository references inside Pydantic validators

Rejected because domain object construction should not depend on filesystem state or a specific persistence implementation.

## Deferred

- repository persistence for research-state objects;
- transition commands/workflow APIs;
- authenticated human identity;
- Decision amendment/revocation semantics;
- research-state conflict resolution;
- Claim/Evidence approval semantics;
- agent recommendation objects.
