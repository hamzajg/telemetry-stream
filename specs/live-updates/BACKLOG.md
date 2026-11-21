# Backlog: live-updates

Items are USER STORIES in the parseable format below — keep the heading
shape `## US<n> — <story>` and the field lines intact so `wave_plan` can
parse them. Write the story as: "As a <role>, I want <goal>, so that
<value>" — the title after the dash IS the story.

## US1 — As a fleet/operations operator, I want newly ingested telemetry events pushed to my dashboard via WebSocket, so that I see live updates without refreshing
- Scenarios: @w1
- Size: M
- Notes: FastAPI WebSocket broadcast from ingest handler; frontend WS client on mount

## US2 — As a fleet/operations operator, I want previously loaded events to remain visible if the WebSocket disconnects, so that I don't lose context
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: keep polling table data; reconnect WS on close

Order stories by user value; dependencies express technical order only.
