# Validation — telemetry-ingestion

## Traceability

| AC | Criterion | Scenarios | Wave(s) | Test evidence |
|----|-----------|-----------|---------|---------------|
| 1 | A valid telemetry event is accepted and assigned a… | event failing schema validation is rejected and not persisted, valid telemetry event is accepted with a per-device offset | 1 | (weak) test_domain.py, test_kafka_bus.py |
| 2 | Events for the same device are delivered in emission order | any ingestion instance can accept events for any device, events for the same device are delivered in emission order | 2 | test_kafka_bus.py |
| 3 | An event failing schema validation is rejected with a typed… | event failing schema validation is rejected and not persisted, valid telemetry event is accepted with a per-device offset | 1 | (weak) test_domain.py, test_kafka_bus.py |
| 4 | The ingestion service is stateless: any instance can accept… | any ingestion instance can accept events for any device, events for the same device are delivered in emission order | 2 | test_kafka_bus.py |
| 5 | Stored events are replayable from the bus offset for… | stored events are replayable from a bus offset | 3 | (weak) test_kafka_bus.py, test_lakehouse.py |

## Scenario coverage

- Scenarios: 5 total, 1 with detected test evidence, 4 with weak (token-match) evidence only, 0 without
- ~ `valid telemetry event is accepted with a per-device offset` (@w1)
- ~ `events for the same device are delivered in emission order` (@w2)
- ~ `event failing schema validation is rejected and not persisted` (@w1)
- ✓ `any ingestion instance can accept events for any device` (@w2)
- ~ `stored events are replayable from a bus offset` (@w3)

## Demo script (manual walkthrough)

1. **valid telemetry event is accepted with a per-device offset** — run the app, perform the scenario, observe the outcome.

## Gaps

- none — spec is fully traced

Note: 'no evidence' means neither the scenario name nor a
token match was found in test files — verify by hand before
treating it as a real gap. '~' marks weak token-match evidence.

## Outcome follow-up

Optional; this is a post-release learning record, not a finish gate.
- Status: not yet measured
- Owner and review date: (record when known)
- Signal and observed result: (record after release; do not invent)
- Learning or next action: (record after review)