# Backlog: frontend

Items are USER STORIES in the parseable format below — keep the heading
shape `## US<n> — <story>` and the field lines intact so `wave_plan` can
parse them. Write the story as: "As a <role>, I want <goal>, so that
<value>" — the title after the dash IS the story.

## US1 — As a fleet/operations operator, I want to see live telemetry events on a dashboard, so that I can monitor device activity in real time
- Scenarios: @w1
- Size: M
- Notes: happy path; fetch from FastAPI /events endpoint

## US2 — As a fleet/operations operator, I want to filter telemetry by device id, so that I can focus on a specific device
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: client-side filter over fetched events

## US3 — As a fleet/operations operator, I want emergency-incident events to surface as incidents, so that I can respond to incidents quickly
- Scenarios: @w2
- Depends: US1
- Size: M
- Notes: identify incident-type events and highlight them

## US4 — As a platform operator, I want to see the device registry with active count and registration details, so that I know which devices are registered
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: fetch from FastAPI /devices endpoint

## US5 — As a platform operator, I want to see accept/reject counters and consumer lag, so that I can observe ingestion health
- Scenarios: @w3
- Depends: US1
- Size: M
- Notes: fetch observability metrics from backend endpoints

Order stories by user value; dependencies express technical order only.
