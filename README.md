# Telemetry Stream

Realtime ingestion, processing, and storage of IoT telemetry from mobile and
fixed edge devices. Producers emit events to a durable message bus; a stream
consumer reads, schemas, and persists the data to a lakehouse/analytics layer
for downstream query and transformation.

## Stack

Backend: Python (stdlib-first domain core, FastAPI HTTP adapter).
Event bus: Apache Kafka (Redpanda in dev) — durable, ordered, replayable.
Schema: minimal JSON schema adapter (swappable for Avro/JSON Schema behind the same port).
Justification: stdlib-only domain core runs without any framework/HTTP/bus; Kafka provides per-device ordering via partition key, durability, and replay; hexagonal layout keeps business rules framework-independent and fast to test.

## Shipped features

### telemetry-ingestion — done, acceptance-validated (3 waves, 5 stories, 5 scenarios)

- AC1: valid event accepted with per-device offset
- AC2: per-device events delivered in emission order
- AC3: invalid-schema events rejected, not persisted
- AC4: stateless — any instance accepts any device
- AC5: events replayable from a bus offset

21/21 tests pass (17 unit stdlib-only + 4 integration against real Kafka/Redpanda).

### stream-processing — done, acceptance-validated (3 waves, 5 stories, 4 scenarios)

- AC1: consumed event updates current device state (projection read model)
- AC2: per-device events consumed in emission order
- AC3: invalid-schema events skipped, not projected, error counted
- AC4: stateless consumer — any instance consumes any device
- AC5: events replayable from a bus offset for recovery

38/38 tests pass (35 unit stdlib-only + 3 integration against real Kafka/Redpanda).

### lakehouse-storage — done, acceptance-validated (3 waves, 5 stories, 4 scenarios)

- AC1: projected event written to lakehouse partitioned by device_id and date
- AC2: writes idempotent — same offset never duplicates
- AC3: registered table queryable after write batch
- AC4: stateless writer — any instance writes any device
- AC5: rows recoverable from committed offset after restart (inherent in idempotent offset-keyed writes)

49/49 tests pass (35 unit stdlib-only + 14 integration vs Kafka/Redpanda + local object storage).

## Delivery

This repo is managed by OpenHarness. Product work flows through
`specs/<feature>/` and the `/ship-loop` delivery loop. One wave = one branch =
one PR.

## Repo rules

- No secrets or credentials in code; use environment variables or placeholders.
- No framework leakage into domain modules (see `SELF/PRINCIPLES.md` D001–D014).
- Design decisions are recorded in `SPEC.md → ## Decisions` and reviewed with
  `/challenge-decision` before wave planning (gate G1).
- Specs and deliveries are independently audited (`review_delivery`) before
  planning and before finish.
