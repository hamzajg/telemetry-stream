# Backlog: telemetry-ingestion

Items are USER STORIES in the parseable format below — keep the heading
shape `## US<n> — <story>` and the field lines intact so `wave_plan` can
parse them. Write the story as: "As a <role>, I want <goal>, so that
<value>" — the title after the dash IS the story.

## US1 — As a device operator, I want to send a valid telemetry event and have it accepted with a per-device offset, so that I know my event was durably recorded
- Scenarios: @w1
- Size: M
- Notes: happy path acceptance

## US2 — As a stream consumer, I want events for the same device delivered in emission order, so that I can reconstruct device state correctly
- Scenarios: @w2
- Depends: US1
- Size: M
- Notes: per-device ordering via Kafka partition key

## US3 — As a platform operator, I want invalid-schema events rejected with a typed error and not persisted, so that bad data never enters the bus
- Scenarios: @w1
- Size: S
- Notes: schema validation at the adapter boundary

## US4 — As a platform operator, I want any ingestion instance to accept events for any device, so that I can scale horizontally and survive instance loss
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: stateless service; ordering via bus partitioning

## US5 — As a stream consumer, I want to replay stored events from a bus offset, so that I can recover state after a failure
- Scenarios: @w3
- Depends: US2
- Size: M
- Notes: event sourcing; append-only, replayable

Order stories by user value; dependencies express technical order only.
