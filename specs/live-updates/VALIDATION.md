# Validation — live-updates

## Traceability

| AC | Criterion | Scenarios | Wave(s) | Test evidence |
|----|-----------|-----------|---------|---------------|
| 1 | Newly ingested telemetry event is pushed to all connected… | frontend opens WebSocket on dashboard load and displays live events, newly ingested event is pushed to all connected WebSocket clients | 1 | (weak) App.test.tsx |
| 2 | Frontend opens WebSocket on dashboard load and displays… | frontend opens WebSocket on dashboard load and displays live events, newly ingested event is pushed to all connected WebSocket clients | 1 | (weak) App.test.tsx |
| 3 | WebSocket disconnect/reconnect does not lose previously… | WebSocket disconnect does not lose previously loaded events | 2 | — |

## Scenario coverage

- Scenarios: 3 total, 0 with detected test evidence, 1 with weak (token-match) evidence only, 2 without
- ✗ `newly ingested event is pushed to all connected WebSocket clients` (@w1)
- ~ `frontend opens WebSocket on dashboard load and displays live events` (@w1)
- ✗ `WebSocket disconnect does not lose previously loaded events` (@w2)

## Demo script (manual walkthrough)

1. **newly ingested event is pushed to all connected WebSocket clients** — run the app, perform the scenario, observe the outcome.

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