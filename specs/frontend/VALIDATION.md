# Validation — frontend

## Traceability

| AC | Criterion | Scenarios | Wave(s) | Test evidence |
|----|-----------|-----------|---------|---------------|
| 1 | Dashboard loads and displays live telemetry events from the backend | dashboard loads and displays live telemetry events | 1 | (weak) App.test.tsx |
| 2 | Operator can filter telemetry by device id | operator filters telemetry by device id | 2 | (weak) App.test.tsx |
| 3 | Emergency-incident events surface as incidents/alerts | emergency-incident events surface as incidents | 2 | App.test.tsx |
| 4 | Device registry shows active count and registration details | device registry shows active count and registration details | 2 | (weak) App.test.tsx |
| 5 | Observability panel shows accept/reject counters and consumer lag | observability panel shows accept/reject counters and consumer lag | 3 | App.test.tsx |

## Scenario coverage

- Scenarios: 5 total, 2 with detected test evidence, 3 with weak (token-match) evidence only, 0 without
- ~ `dashboard loads and displays live telemetry events` (@w1)
- ~ `operator filters telemetry by device id` (@w2)
- ✓ `emergency-incident events surface as incidents` (@w2)
- ~ `device registry shows active count and registration details` (@w2)
- ✓ `observability panel shows accept/reject counters and consumer lag` (@w3)

## Demo script (manual walkthrough)

1. **dashboard loads and displays live telemetry events** — run the app, perform the scenario, observe the outcome.
2. **operator filters telemetry by device id** — enter a device id in the filter, observe only matching events.
3. **emergency-incident events surface as incidents** — ingest an emergency_incident event, observe the row highlighted.
4. **device registry shows active count and registration details** — open the Devices view, observe active count and device list.
5. **observability panel shows accept/reject counters and consumer lag** — open the Observability view, observe counters and lag.

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
