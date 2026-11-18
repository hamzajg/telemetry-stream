# Validation — lakehouse-storage

## Traceability

| AC | Criterion | Scenarios | Wave(s) | Test evidence |
|----|-----------|-----------|---------|---------------|
| 1 | A projected telemetry event is written to the lakehouse… | projected telemetry event is written to lakehouse partitioned by device_id and date | 1 | test_lakehouse.py |
| 2 | Lakehouse writes are idempotent: replaying the same offset… | lakehouse writer is stateless — any instance can write any device, lakehouse writes are idempotent — replaying same offset does not duplicate | 2 | test_lakehouse.py |
| 3 | A registered table is queryable (schema + rows visible)… | projected telemetry event is written to lakehouse partitioned by device_id and date | 1 | test_lakehouse.py |
| 4 | Lakehouse writer is stateless: any instance can write any… | lakehouse writer is stateless — any instance can write any device, lakehouse writes are idempotent — replaying same offset does not duplicate | 2 | test_lakehouse.py |
| 5 | Stored lakehouse rows are recoverable from a committed… | stored lakehouse rows are recoverable from a committed offset after restart | 3 | test_lakehouse.py |

## Scenario coverage

- Scenarios: 4 total, 4 with detected test evidence, 0 without
- ✓ `projected telemetry event is written to lakehouse partitioned by device_id and date` (@w1)
- ✓ `lakehouse writes are idempotent — replaying same offset does not duplicate` (@w2)
- ✓ `lakehouse writer is stateless — any instance can write any device` (@w2)
- ✓ `stored lakehouse rows are recoverable from a committed offset after restart` (@w3)

## Demo script (manual walkthrough)

1. **projected telemetry event is written to lakehouse partitioned by device_id and date** — run the app, perform the scenario, observe the outcome.

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