# Spec: telemetry-ingestion

> Spec-driven development artifact. This file is the contract: implementation
> is done when every acceptance criterion maps to a scenario in
> `EXAMPLES.feature` and every scenario has a passing check.

## Problem

Edge devices (vehicles, cameras, weather stations, emergency sensors) emit
telemetry events continuously, but there is no durable, ordered intake path
that accepts events from many producers, persists them as immutable facts,
and makes them available to downstream consumers. Lost or reordered events
mean the stream consumer cannot reconstruct device state or detect incidents
reliably.

## Users

- Device operator — sends telemetry from field devices and needs confidence
  that every event is durably accepted in order.
- Stream consumer — reads a schema-bound, replayable event stream to project
  device state and detect incidents.
- Platform operator — runs the ingestion stack and needs observability into
  accept/reject rates and lag.

## Outcome hypothesis

- Expected user outcome: every telemetry event from a registered device is
  durably accepted, ordered per device, and readable by the stream consumer
  within seconds of emission.
- Opportunity evidence: assumption — sourced from the library course
  section titles (IoT Data Producer, Realtime Streaming Consumer); not yet
  validated against production telemetry volume.
- Signal: events accepted per second, events rejected per second, end-to-end
  lag from producer emit to consumer read (baseline unknown; do not invent
  targets).
- Follow-up owner/date: platform operator — review after wave 1 ships.

## Scope (in)

- `ingest` domain: accept telemetry events, validate schema, enforce
  per-device ordering, append as immutable facts.
- `transport` adapter: Kafka as the durable, replayable event bus (event
  store).
- `schema` adapter: Avro/JSON schema enforced at the consumer boundary.
- Observability: accept/reject counters, consumer lag.

## Scope (out)

- Stream processing / projections (Spark consumer) — later feature.
- Lakehouse storage (S3/Glue/Athena/Redshift) — later feature.
- Device registration / provisioning — later feature.
- Authentication / authorization for producers — later feature (API keys
  via env vars/placeholders only in MVP).
- Web UI / dashboards — later feature.

## Acceptance criteria

| # | Criterion | Scenario(s) |
|---|-----------|-------------|
| 1 | A valid telemetry event is accepted and assigned a monotonically increasing offset per device | @w1 |
| 2 | Events for the same device are delivered in emission order | @w2 |
| 3 | An event failing schema validation is rejected with a typed error and not persisted | @w1 |
| 4 | The ingestion service is stateless: any instance can accept events for any device | @w2 |
| 5 | Stored events are replayable from the bus offset for consumer recovery | @w3 |

## Decisions

### D1 — Stateless vs stateful ingestion service

- Context & forces: The service must accept events from many concurrent
  devices and scale horizontally. A stateful service pins devices to
  instances, complicates deployments, and loses events on instance
  failure. A stateless service lets any instance accept any device's events
  and is trivial to roll out/roll back.
- Options considered:
  1. Stateful, device-affinity instances (simplest to reason about per
     device, but not horizontally scalable, not resilient to instance loss).
  2. Stateless ingestion service with ordering enforced in the event bus
     (horizontal scale, resilient, but ordering must be guaranteed by the
     bus, not by instance affinity).
- Decision & why: Stateless ingestion service. Kafka partitions by device
  id provide per-device ordering; the service itself holds no device state,
  so any instance can accept any event and instances are interchangeable.
- Consequences:
  - Positive: horizontal scale, zero-downtime deploys, instance loss is
    non-fatal, simple ops.
  - Negative: per-device ordering depends on Kafka partitioning; a bad
    partition key breaks ordering; the service cannot validate
  cross-device invariants locally (none required by scope).
- Reversibility: two-way door — adding instance affinity later is a config
  change, but moving away from it requires re-partitioning history.

### D2 — Event sourcing vs entity model for persistence

- Context & forces: The ingestion layer persists telemetry events. An
  entity model stores current device state (upserts) and loses history;
  event sourcing appends immutable facts and supports replay, audit, and
  consumer recovery. The downstream consumer needs to reconstruct device
  state and detect incidents over time.
- Options considered:
  1. Entity model: one row per device with latest values (simple queries,
     no history, cannot replay, cannot detect temporal patterns).
  2. Event sourcing: append-only stream of telemetry events keyed by device
     (full history, replayable, supports consumer recovery, requires
     projection to read current state).
- Decision & why: Event sourcing. Kafka is the append-only event store;
  each telemetry event is an immutable fact with a per-sequence offset.
  Current device state is a projection derived by the consumer, not stored
  by ingestion.
- Consequences:
  - Positive: full history, replayability, audit, consumer can rebuild
    state after failure, matches the durable-bus requirement.
  - Negative: no "current state" read from ingestion (consumer must
    project); event schema evolution needs care.
- Reversibility: one-way door for the event store choice — migrating from
  an entity model to event sourcing requires replaying history; reversing
  means losing the replay benefit. Revisit trigger: if query latency for
  current state becomes a bottleneck, add a materialized projection (does
  not remove the event store).

### D3 — Persistence: in-memory vs durable bus

- Context & forces: In-memory persistence is fast but loses events on
  restart and cannot support multiple consumers or replay. A durable bus
  (Kafka) survives restarts, supports many consumer groups, and enables
  replay. The requirement is durable intake and consumer recovery.
- Options considered:
  1. In-memory queue (fast, simple, zero ops, but volatile, single
     consumer, no replay).
  2. Durable bus: Kafka (ops overhead, but durable, replayable, multi
     consumer, ordered partitions).
- Decision & why: Durable bus (Kafka). In-memory is acceptable only for a
  throwaway prototype; it fails the durability and replay requirements.
- Consequences:
  - Positive: survives restarts, multiple consumer groups, replay, exactly
    once semantics with idempotent producers.
  - Negative: ops complexity (ZooKeeper/Kafka cluster), schema management,
    capacity planning.
- Reversibility: two-way door behind an adapter — the domain depends on a
  `TelemetryBus` port; swapping Kafka for another durable bus (or an
  in-memory test double) is an adapter change, not a domain change.

### D4 — Module layout: hexagonal (ports & adapters)

- Context & forces: The core domain (accept, validate, order, append) must
  be testable without Kafka, S3, or a web framework. Framework leakage into
  the domain makes tests slow and couples business rules to infrastructure.
- Options considered:
  1. Layered (controllers → services → repositories) with the ORM/framework
     imported in the service layer (simple, but domain depends on framework).
  2. Hexagonal: domain core depends on nothing; ports define interfaces;
     adapters implement Kafka, HTTP, S3 (more files, but domain is pure and
     fast to test).
- Decision & why: Hexagonal (ports & adapters). Domain core imports no
  framework, ORM, or HTTP library. Adapters implement the `TelemetryBus`,
  `TelemetrySchema`, and `TelemetryApi` ports.
- Consequences:
  - Positive: domain core tests run without Kafka/DB/framework; adapters
    can be swapped or stubbed; business rules are framework-independent.
  - Negative: more abstractions up front; boilerplate for port/adapter
    mapping.
- Reversibility: two-way door — collapsing to layered later is a
  refactor, not a rewrite.

## Stack decision

- Backend: Python (stdlib-first domain core, FastAPI HTTP adapter).
  Justification: stdlib-only domain core runs without any framework/HTTP/bus;
  Kafka provides per-device ordering via partition key, durability, and
  replay; hexagonal layout keeps business rules framework-independent and
  fast to test.
- Event bus: Apache Kafka (per D2/D3).
- Schema: Avro or JSON Schema (per D3).
