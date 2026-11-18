# Backlog: lakehouse-storage

Items are USER STORIES in the parseable format below — keep the heading
shape `## US<n> — <story>` and the field lines intact so `wave_plan` can
parse them. Write the story as: "As a <role>, I want <goal>, so that
<value>" — the title after the dash IS the story.

## US1 — As a data analyst, I want projected telemetry events written to the lakehouse partitioned by device_id and date, so that I can query historical readings
- Scenarios: @w1
- Size: M
- Notes: Parquet partitioned by device_id and event date

## US2 — As a platform operator, I want lakehouse writes to be idempotent, so that replaying the same offset does not duplicate rows
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: idempotent writes keyed by device_id + offset

## US3 — As a data analyst, I want a registered table to be queryable after a write batch, so that I can run ad-hoc analytics
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: Glue crawler / local catalog registration

## US4 — As a platform operator, I want the lakehouse writer to be stateless, so that any instance can write any device's events
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: stateless writer, idempotent writes

## US5 — As a data analyst, I want stored lakehouse rows recoverable from a committed offset after a restart, so that I can recover state after a failure
- Scenarios: @w3
- Depends: US2
- Size: M
- Notes: offset-based recovery from object store

Order stories by user value; dependencies express technical order only.
