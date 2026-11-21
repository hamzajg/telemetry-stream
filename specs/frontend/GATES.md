# Gates: frontend

> Preconditions for phase transitions. Each `## G<n> — <title>` block is a
> gate. `ship_loop` refuses to advance past a phase while a blocking gate is
> pending. Definitions live here; status and evidence live in `LOOP.md`.
>
> Gate phases: `spec` (before writing the spec), `plan` (before planning
> waves), `wave:<n>` (before starting wave n), `validate` (before validation),
> `finish` (before closing the feature).
>
> Gate types: decision | artifact | external | technical | quality | data.
> Resolver: `human` (needs a person to decide/provide something) or `agent`
> (the agent can satisfy it). Check: `manual`, `file:<repo-relative-path>`, or
> `command:<exact command>` (the agent runs it and records the output as
> evidence — the oracle never executes it).

## G1 — Design decisions challenged
- Before: plan
- Type: artifact
- Owner: agent
- Resolver: agent
- Blocking: yes
- Check: file:specs/frontend/DECISION-REVIEW.md
- Why: Every wave inherits the feature's architecture choices (stack, data
  fetch model, module boundaries). The challenger review — alternatives,
  tradeoffs, testability — must exist before wave planning locks the design
  in. A human may waive this gate for genuinely trivial features.

## G2 — Frontend stack chosen and recorded
- Before: spec
- Type: decision
- Owner: agent
- Resolver: agent
- Blocking: yes
- Check: file:specs/frontend/SPEC.md
- Why: The frontend stack (React + TypeScript + Vite) and data fetch model
  (polling over HTTP) must be recorded as ADR-style decisions in SPEC.md
  before any implementation begins, so the team knows the contract and can
  review tradeoffs.
