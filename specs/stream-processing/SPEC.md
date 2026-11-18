# Spec: stream-processing

> Spec-driven development artifact. This file is the contract: implementation
> is done when every acceptance criterion maps to a scenario in
> `EXAMPLES.feature` and every scenario has a passing check.

## Problem

Telemetry events are durably accepted into Kafka by the ingestion feature,
but there is no consumer that reads them, applies schema, and projects current
device state. Operators cannot see "where is device X now" or detect an
incident because they must replay the whole event stream to reconstruct state.

## Users

- Stream consumer operator — runs the Spark job that reads Kafka and writes
  projections.
- Device operator — queries current device state (location, last reading) and
  needs it to reflect recently ingested events.
- Platform operator — observes consumer lag and accept/reject rates for the
  processing pipeline.

## Outcome hypothesis

- Expected user outcome: current device state is available within seconds of
  event ingestion, without replaying history.
- Opportunity evidence: assumption — sourced from the library course
  section titles (Realtime Streaming Consumer); not yet validated against
  production volume.
- Signal: consumer lag (events ingested minus events projected), projection
  freshness (time from event timestamp to projection update) (baseline
  unknown; do not invent targets).
- Follow-up owner/date: platform operator — review after wave 1 ships.

## Scope (in)

- `stream` domain: read telemetry events from Kafka, validate schema, project
  current device state (event sourcing read model).
- `projection` adapter: in-memory current-state store for wave 1 (swappable
  for a DB later).
- `transport` adapter: Kafka consumer (reuses the `TelemetryBus` read port
  from telemetry-ingestion).
- Observability: consumer lag, events projected per second, projection errors.

## Scope (out)

- Lakehouse storage (S3/Glue/Athena/Redshift) — later feature.
- Device registration / provisioning — later feature.
- Authentication / authorization for consumers — later feature.
- Web UI / dashboards — later feature.
- Exactly-once semantics beyond Kafka at-least-once + idempotent projection
  writes — later feature (wave 1 uses at-least-once with dedup by offset).

## Acceptance criteria

<!-- Scenario(s): use scenario names verbatim from EXAMPLES.feature and/or
     @w<N> tags — ship_validate resolves both for traceability. -->

| # | Criterion | Scenario(s) |
|---|-----------|-------------|
| 1 | A consumed telemetry event updates current device state (latest reading per device) | @w1 |
| 2 | Consumer reads events in per-device emission order from Kafka | @w2 |
| 3 | An event failing schema validation is skipped and not projected, with an error counted | @w1 |
| 4 | Consumer is stateless across restarts: projection rebuilds from last committed offset | @w1 |
| 5 | Stored events are replayable from a bus offset for consumer recovery | @w3 |

## Decisions

### D1 — Stateless vs stateful stream processor

- Context & forces: The processor must read Kafka continuously and maintain
  current device state. A fully stateful processor pins devices to task slots
  and complicates restarts. A stateless processor (one event at a time,
  projection keyed by device_id) lets any task handle any device and is
  trivial to restart.
- Options considered:
  1. Stateful, device-affinity Spark tasks (complex restarts, slot pinning).
  2. Stateless per-event projection (any task handles any device, simple
     restart, ordering guaranteed by Kafka partition).
- Decision & why: Stateless per-event projection. Kafka partitions by device
  id provide per-device ordering; the processor holds no device affinity,
  so any task can process any event and tasks are interchangeable.
- Consequences:
  - Positive: horizontal scale, simple restarts, no task pinning.
  - Negative: per-device ordering depends on Kafka partitioning; cross-device
    invariants not checked locally (none required by scope).
- Reversibility: two-way door — adding task affinity later is a config
  change.

### D2 — Read model: projection vs query-on-read

- Context & forces: Operators need current device state. Query-on-read
  replays the event stream per query (slow, no history bound). A projection
  stores current state per device (fast reads, bounded storage, needs rebuild
  on schema change).
- Options considered:
  1. Query-on-read: replay events per device query (simple, no projection
     store, but O(history) per query).
  2. Projection: maintain current state per device, updated per event (fast
     O(1) reads, needs a store, rebuild on schema change).
- Decision & why: Projection. Current device state is read frequently and
  must be fast; event history remains in Kafka (the source of truth) for
  rebuild/audit.
- Consequences:
  - Positive: O(1) state reads, Kafka remains the durable source of truth.
  - Negative: projection store is a second write path; schema changes need a
    rebuild.
- Reversibility: two-way door — query-on-read can be added as an alternative
  read path later.

### D3 — Persistence: in-memory projection vs database

- Context & forces: Wave 1 needs a projection store. In-memory is fast but
  volatile; a database is durable but adds ops. The source of truth is Kafka,
  so projection loss is recoverable by replay.
- Options considered:
  1. In-memory projection (fast, volatile, zero ops, recoverable from Kafka).
  2. Database projection (durable, ops overhead, but projection loss is still
     recoverable from Kafka).
- Decision & why: In-memory projection for wave 1. Kafka is the source of
  truth; losing the projection only costs a replay. Simpler, faster
  iteration.
- Consequences:
  - Positive: zero ops, fast tests, replayable from Kafka.
  - Negative: projection lost on restart until rebuilt; single instance only.
- Reversibility: two-way door behind an adapter — swapping to a database is
  an adapter change.

### D4 — Module layout: hexagonal (ports & adapters)

- Context & forces: The stream domain (read, validate, project) must be
  testable without Kafka, Spark, or a database.
- Options considered:
  1. Layered with Spark imports in the domain (simple, domain depends on
     framework).
  2. Hexagonal: domain core depends on nothing; ports define interfaces;
     adapters implement Kafka, projection store (more files, domain is pure
     and fast to test).
- Decision & why: Hexagonal (ports & adapters). Domain core imports no
  framework, ORM, or HTTP library.
- Consequences:
  - Positive: domain core tests run without Kafka/Spark/DB; adapters
    swappable/stubbed.
  - Negative: more abstractions up front.
- Reversibility: two-way door.

## Stack decision

- Backend: Python (stdlib-first domain core, PySpark consumer adapter).
  Justification: domain core stays framework-free; PySpark is the stream
  consumer per the library course section (Realtime Streaming Consumer).
- Event bus: Apache Kafka (Redpanda in dev), reused from telemetry-ingestion.
- Projection store: in-memory dict (wave 1, swappable for a DB).
