# Telemetry Stream

Realtime ingestion, processing, and storage of IoT telemetry from mobile and
fixed edge devices. Producers emit events to a durable message bus; a stream
consumer reads, schemas, and persists the data to a lakehouse/analytics layer
for downstream query and transformation.

## Stack

TBD — record the one-line justification as an ADR/decision in
`specs/<feature>/SPEC.md`.

## Delivery

This repo is managed by OpenHarness. Product work flows through
`specs/<feature>/` and the `/ship-loop` delivery loop. One wave = one branch =
one PR.

## Repo rules

- No secrets or credentials in code; use environment variables or placeholders.
- No framework leakage into domain modules (see `SELF/PRINCIPLES.md` D001–D014).
- Design decisions are recorded in `SPEC.md → ## Decisions` and reviewed with
  `/challenge-decision` before wave planning (gate G1).
- Specs and deliveries are independently audited (`review_delivery`) before
  planning and before finish.
