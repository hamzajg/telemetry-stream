# Waves — telemetry-ingestion

Each wave IS an iteration: a time-boxed, independently shippable
increment — one branch, one PR, green tests, demoable outcome.
Do not start wave N+1 until wave N merges.

## Wave 1 — iteration 1

Scenarios proven by this wave:
- valid telemetry event is accepted with a per-device offset
- event failing schema validation is rejected and not persisted

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US1 | As a device operator, I want to send a valid telemetry event and have it accepted with a per-device offset, so that I know my event was durably recorded | M | — | happy path acceptance |
| US3 | As a platform operator, I want invalid-schema events rejected with a typed error and not persisted, so that bad data never enters the bus | S | — | schema validation at the adapter boundary |

## Wave 2 — iteration 2

Scenarios proven by this wave:
- events for the same device are delivered in emission order
- any ingestion instance can accept events for any device

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US2 | As a stream consumer, I want events for the same device delivered in emission order, so that I can reconstruct device state correctly | M | US1 | per-device ordering via Kafka partition key |
| US4 | As a platform operator, I want any ingestion instance to accept events for any device, so that I can scale horizontally and survive instance loss | S | US1 | stateless service; ordering via bus partitioning |

## Wave 3 — iteration 3

Scenarios proven by this wave:
- stored events are replayable from a bus offset

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US5 | As a stream consumer, I want to replay stored events from a bus offset, so that I can recover state after a failure | M | US2 | event sourcing; append-only, replayable |
