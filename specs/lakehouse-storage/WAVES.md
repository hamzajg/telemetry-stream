# Waves — lakehouse-storage

Each wave IS an iteration: a time-boxed, independently shippable
increment — one branch, one PR, green tests, demoable outcome.
Do not start wave N+1 until wave N merges.

## Wave 1 — iteration 1

Scenarios proven by this wave:
- projected telemetry event is written to lakehouse partitioned by device_id and date

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US1 | As a data analyst, I want projected telemetry events written to the lakehouse partitioned by device_id and date, so that I can query historical readings | M | — | Parquet partitioned by device_id and event date |

## Wave 2 — iteration 2

Scenarios proven by this wave:
- lakehouse writes are idempotent — replaying same offset does not duplicate
- lakehouse writer is stateless — any instance can write any device

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US2 | As a platform operator, I want lakehouse writes to be idempotent, so that replaying the same offset does not duplicate rows | S | US1 | idempotent writes keyed by device_id + offset |
| US3 | As a data analyst, I want a registered table to be queryable after a write batch, so that I can run ad-hoc analytics | S | US1 | Glue crawler / local catalog registration |
| US4 | As a platform operator, I want the lakehouse writer to be stateless, so that any instance can write any device's events | S | US1 | stateless writer, idempotent writes |

## Wave 3 — iteration 3

Scenarios proven by this wave:
- stored lakehouse rows are recoverable from a committed offset after restart

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US5 | As a data analyst, I want stored lakehouse rows recoverable from a committed offset after a restart, so that I can recover state after a failure | M | US2 | offset-based recovery from object store |
