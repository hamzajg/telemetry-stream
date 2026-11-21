# Waves — frontend

Each wave IS an iteration: a time-boxed, independently shippable
increment — one branch, one PR, green tests, demoable outcome.
Do not start wave N+1 until wave N merges.

## Wave 1 — iteration 1

Scenarios proven by this wave:
- dashboard loads and displays live telemetry events

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US1 | As a fleet/operations operator, I want to see live telemetry events on a dashboard, so that I can monitor device activity in real time | M | — | happy path; fetch from FastAPI /events endpoint |

## Wave 2 — iteration 2

Scenarios proven by this wave:
- operator filters telemetry by device id
- emergency-incident events surface as incidents
- device registry shows active count and registration details

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US2 | As a fleet/operations operator, I want to filter telemetry by device id, so that I can focus on a specific device | S | US1 | client-side filter over fetched events |
| US3 | As a fleet/operations operator, I want emergency-incident events to surface as incidents, so that I can respond to incidents quickly | M | US1 | identify incident-type events and highlight them |
| US4 | As a platform operator, I want to see the device registry with active count and registration details, so that I know which devices are registered | S | US1 | fetch from FastAPI /devices endpoint |

## Wave 3 — iteration 3

Scenarios proven by this wave:
- observability panel shows accept/reject counters and consumer lag

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US5 | As a platform operator, I want to see accept/reject counters and consumer lag, so that I can observe ingestion health | M | US1 | fetch observability metrics from backend endpoints |
