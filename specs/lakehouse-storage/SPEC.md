# Spec: lakehouse-storage

> Spec-driven development artifact. This file is the contract: implementation
> is done when every acceptance criterion maps to a scenario in
> `EXAMPLES.feature` and every scenario has a passing check.

## Problem

Stream-processed telemetry projections live only in memory and are lost on
restart. Operators cannot query historical telemetry, audit device state over
time, or run analytics without rebuilding from Kafka every time. A durable,
queryable lakehouse is needed on top of the event stream.

## Users

- Data analyst — queries historical telemetry and runs ad-hoc analytics.
- Platform operator — runs Glue crawlers and monitors lakehouse freshness.
- Device operator — investigates incidents by looking up historical readings.

## Outcome hypothesis

- Expected user outcome: historical telemetry is queryable within minutes of
  ingestion, without replaying Kafka from the beginning.
- Opportunity evidence: assumption — sourced from the library course section
  titles (Streaming data to s3 lakehouse, Creating AWS Glue crawlers,
  Querying data with AWS Athena); not yet validated against production volume.
- Signal: lakehouse freshness (time from event ingest to queryable), query
  latency, rows loaded per batch (baseline unknown; do not invent targets).
- Follow-up owner/date: platform operator — review after wave 1 ships.

## Scope (in)

- `lakehouse` domain: write projected telemetry events to object storage in a
  queryable, partitioned format; register tables for analytics.
- `storage` adapter: object store (S3 in prod, local filesystem in tests)
  writing Parquet/JSONL partitioned by device_id and event date.
- `catalog` adapter: table registration (Glue crawler in prod, local catalog
  in tests).
- Observability: rows written per batch, lakehouse lag, queryable freshness.

## Scope (out)

- Stream processing / projections — earlier feature.
- Device registration / provisioning — later feature.
- Authentication / authorization for lakehouse access — later feature.
- Redshift / data warehouse loading — later feature (Athena is the query
  layer for wave 1).
- Web UI / dashboards — later feature.

## Acceptance criteria

<!-- Scenario(s): use scenario names verbatim from EXAMPLES.feature and/or
     @w<N> tags — ship_validate resolves both for traceability. -->

| # | Criterion | Scenario(s) |
|---|-----------|-------------|
| 1 | A projected telemetry event is written to the lakehouse partitioned by device_id and date | @w1 |
| 2 | Lakehouse writes are idempotent: replaying the same offset does not duplicate rows | @w2 |
| 3 | A registered table is queryable (schema + rows visible) after a write batch | @w1 |
| 4 | Lakehouse writer is stateless: any instance can write any device's events | @w2 |
| 5 | Stored lakehouse rows are recoverable from a committed offset after a restart | @w3 |

## Decisions

### D1 — Stateless vs stateful lakehouse writer

- Context & forces: The writer must read projected events and persist them to
  object storage. A stateful writer pins devices/writers to instances and
  complicates restarts. A stateless writer (any instance writes any device)
  with idempotent writes is trivial to restart and scale.
- Options considered:
  1. Stateful, device-affinity writer instances (complex restarts, slot
     pinning).
  2. Stateless per-event writer (any instance writes any device, idempotent
     writes keyed by device_id + offset).
- Decision & why: Stateless per-event writer. Object storage keys by
  device_id + offset provide idempotency; the writer holds no device affinity,
  so any instance can write any event and instances are interchangeable.
- Consequences:
  - Positive: horizontal scale, simple restarts, no writer pinning.
  - Negative: per-device write ordering depends on partitioning; cross-device
    consistency not guaranteed locally (none required by scope).
- Reversibility: two-way door — adding writer affinity later is a config
  change.

### D2 — Storage format: Parquet vs JSONL vs raw

- Context & forces: Lakehouse rows must be queryable. Raw JSON is simple but
  not columnar (slow analytics). Parquet is columnar and compressible but
  requires a library. JSONL is line-oriented and easy to append but not
  columnar.
- Options considered:
  1. Raw JSON append (simple, not queryable efficiently).
  2. JSONL append (line-oriented, append-friendly, not columnar).
  3. Parquet (columnar, compressible, queryable by Athena/Glue, requires
     pyarrow library).
- Decision & why: Parquet. Columnar storage enables efficient analytics
  queries (the lakehouse purpose); Glue/Athena natively read Parquet.
- Consequences:
  - Positive: columnar queries, compression, Athena/Glue native support.
  - Negative: pyarrow dependency; batch-oriented (not single-event append).
- Reversibility: two-way door behind an adapter — swapping to JSONL later is
  an adapter change.

### D3 — Persistence: object store vs database

- Context & forces: Lakehouse storage must be durable and queryable. A
  database is queryable but not a "lakehouse"; object storage is the
  lakehouse pattern with a catalog layer on top.
- Options considered:
  1. Database (queryable, ops overhead, not a lakehouse).
  2. Object store + catalog (lakehouse pattern, durable, queryable via
     Glue/Athena).
- Decision & why: Object store (S3) + catalog. Matches the lakehouse
  requirement and the library course (S3 lakehouse → Glue crawlers → Athena).
- Consequences:
  - Positive: durable, cheap, scalable, Athena/Glue compatible.
  - Negative: eventual consistency (object store), batch-oriented writes.
- Reversibility: two-way door behind an adapter — swapping to a database is
  an adapter change.

### D4 — Module layout: hexagonal (ports & adapters)

- Context & forces: The lakehouse domain (write, partition, idempotency) must
  be testable without S3, Glue, or Athena.
- Options considered:
  1. Layered with boto3/glue imports in the domain (simple, domain depends
     on cloud SDK).
  2. Hexagonal: domain core depends on nothing; ports define interfaces;
     adapters implement S3, Glue, local filesystem (more files, domain is
     pure and fast to test).
- Decision & why: Hexagonal (ports & adapters). Domain core imports no
  cloud SDK, ORM, or HTTP library.
- Consequences:
  - Positive: domain core tests run without S3/Glue/Athena; adapters
    swappable/stubbed; local-first dev.
  - Negative: more abstractions up front.
- Reversibility: two-way door.

## Stack decision

- Backend: Python (stdlib-first domain core, boto3 S3 adapter, pyarrow
  Parquet writer).
  Justification: domain core stays framework-free; S3 + Parquet is the
  lakehouse pattern; Glue/Athena query on top.
- Object store: Amazon S3 (local filesystem/Minio in dev, behind the port).
- Format: Parquet (pyarrow).
- Catalog: AWS Glue crawlers (local catalog stub in dev).
