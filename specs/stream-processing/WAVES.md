# Waves — stream-processing

Each wave IS an iteration: a time-boxed, independently shippable
increment — one branch, one PR, green tests, demoable outcome.
Do not start wave N+1 until wave N merges.

## Wave 1 — iteration 1

Scenarios proven by this wave:
- consumed telemetry event updates current device state

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US1 | As a stream consumer operator, I want consumed telemetry events to update current device state, so that I can see the latest reading per device | M | — | projection read model, event sourcing |
| US3 | As a platform operator, I want invalid-schema events skipped and not projected, with an error counted, so that bad data never enters projections | S | — | schema validation at the consumer boundary |

## Wave 2 — iteration 2

Scenarios proven by this wave:
- consumer reads events in per-device emission order from Kafka
- consumer is stateless across restarts

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US2 | As a stream consumer operator, I want events read in per-device emission order from Kafka, so that state reconstruction is correct | M | US1 | Kafka partition key = device_id |
| US4 | As a platform operator, I want the consumer to be stateless across restarts and rebuild from the last committed offset, so that restarts don't duplicate events | S | US1 | stateless consumer, offset commit |

## Wave 3 — iteration 3

Scenarios proven by this wave:
- stored events are replayable from a bus offset

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US5 | As a stream consumer operator, I want to replay stored events from a bus offset, so that I can recover state after a failure | M | US2 | event sourcing; replayable from Kafka offset |
