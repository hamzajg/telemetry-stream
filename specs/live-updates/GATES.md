# Gates: live-updates

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
- Check: file:specs/live-updates/DECISION-REVIEW.md
- Why: WebSocket broadcast and client lifecycle are architectural choices that
  affect every wave. The challenger review must exist before wave planning.

## G2 — WebSocket broadcast and frontend integration chosen and recorded
- Before: spec
- Type: decision
- Owner: agent
- Resolver: agent
- Blocking: yes
- Check: file:specs/live-updates/SPEC.md
- Why: The push model (D1) and frontend integration (D2) must be recorded as
  ADR-style decisions before implementation.
