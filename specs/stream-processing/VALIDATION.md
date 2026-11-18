# Validation — stream-processing

## Traceability

| AC | Criterion | Scenarios | Wave(s) | Test evidence |
|----|-----------|-----------|---------|---------------|
| 1 | A consumed telemetry event updates current device state… | consumed telemetry event updates current device state, consumer is stateless across restarts | 1 | (weak) test_kafka_stream.py |
| 2 | Consumer reads events in per-device emission order from… | consumer is stateless across restarts, consumer reads events in per-device emission order from Kafka | 2 | (weak) test_kafka_stream.py |
| 3 | An event failing schema validation is skipped and not… | consumed telemetry event updates current device state, consumer is stateless across restarts | 1 | (weak) test_kafka_stream.py |
| 4 | Consumer is stateless across restarts: projection rebuilds… | consumed telemetry event updates current device state, consumer is stateless across restarts | 1 | (weak) test_kafka_stream.py |
| 5 | Stored events are replayable from a bus offset for consumer… | stored events are replayable from a bus offset | 3 | (weak) test_kafka_bus.py |

## Scenario coverage

- Scenarios: 4 total, 0 with detected test evidence, 2 with weak (token-match) evidence only, 2 without
- ✗ `consumed telemetry event updates current device state` (@w1)
- ✗ `consumer reads events in per-device emission order from Kafka` (@w2)
- ~ `consumer is stateless across restarts` (@w1, @w2)
- ~ `stored events are replayable from a bus offset` (@w3)

## Demo script (manual walkthrough)

1. **consumed telemetry event updates current device state** — run the app, perform the scenario, observe the outcome.

## Gaps

- 2 scenario(s) lack detected test evidence — verify manually or add checks

Note: 'no evidence' means neither the scenario name nor a
token match was found in test files — verify by hand before
treating it as a real gap. '~' marks weak token-match evidence.

## Outcome follow-up

Optional; this is a post-release learning record, not a finish gate.
- Status: not yet measured
- Owner and review date: (record when known)
- Signal and observed result: (record after release; do not invent)
- Learning or next action: (record after review)