# Backlog: stream-processing

Items are USER STORIES in the parseable format below — keep the heading
shape `## US<n> — <story>` and the field lines intact so `wave_plan` can
parse them. Write the story as: "As a <role>, I want <goal>, so that
<value>" — the title after the dash IS the story.

## US1 — As a stream consumer operator, I want consumed telemetry events to update current device state, so that I can see the latest reading per device
- Scenarios: @w1
- Size: M
- Notes: projection read model, event sourcing

## US2 — As a stream consumer operator, I want events read in per-device emission order from Kafka, so that state reconstruction is correct
- Scenarios: @w2
- Depends: US1
- Size: M
- Notes: Kafka partition key = device_id

## US3 — As a platform operator, I want invalid-schema events skipped and not projected, with an error counted, so that bad data never enters projections
- Scenarios: @w1
- Size: S
- Notes: schema validation at the consumer boundary

## US4 — As a platform operator, I want the consumer to be stateless across restarts and rebuild from the last committed offset, so that restarts don't duplicate events
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: stateless consumer, offset commit

## US5 — As a stream consumer operator, I want to replay stored events from a bus offset, so that I can recover state after a failure
- Scenarios: @w3
- Depends: US2
- Size: M
- Notes: event sourcing; replayable from Kafka offset

Order stories by user value; dependencies express technical order only.
