# Gates: stream-processing

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
- Check: file:specs/stream-processing/DECISION-REVIEW.md
- Why: Every wave inherits the feature's architecture choices (stateless vs
  stateful, projection vs query-on-read, persistence model). The challenger
  review must exist before wave planning locks the design in.

## G2 — Ingestion feature must be complete before stream processing
- Before: plan
- Type: external
- Owner: human
- Resolver: human
- Blocking: yes
- Check: manual
- Why: The stream processor reads events produced by telemetry-ingestion; that
  feature must be merged to main first so the Kafka topic and adapter exist.
