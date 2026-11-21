# Waves — live-updates

Each wave IS an iteration: a time-boxed, independently shippable
increment — one branch, one PR, green tests, demoable outcome.
Do not start wave N+1 until wave N merges.

## Wave 1 — iteration 1

Scenarios proven by this wave:
- newly ingested event is pushed to all connected WebSocket clients
- frontend opens WebSocket on dashboard load and displays live events

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US1 | As a fleet/operations operator, I want newly ingested telemetry events pushed to my dashboard via WebSocket, so that I see live updates without refreshing | M | — | FastAPI WebSocket broadcast from ingest handler; frontend WS client on mount |

## Wave 2 — iteration 2

Scenarios proven by this wave:
- WebSocket disconnect does not lose previously loaded events

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US2 | As a fleet/operations operator, I want previously loaded events to remain visible if the WebSocket disconnects, so that I don't lose context | S | US1 | keep polling table data; reconnect WS on close |
