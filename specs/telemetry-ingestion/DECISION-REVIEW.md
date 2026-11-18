# Decision review brief — Spec: telemetry-ingestion

- Source: `specs/telemetry-ingestion/SPEC.md (## Decisions)`
- Generated: 2026-11-18T05:55:00Z
- Detected type: architecture, data
- Readiness: **CHALLENGE** (6/6 record elements)
- This brief is input to judgment, not a verdict. The agent fills the scorecard after reading the code.

**Reversibility:** stated

**Alternatives on record (verify they are credible, not strawmen):**
- D1 — Stateless vs stateful ingestion service
- D2 — Event sourcing vs entity model for persistence
- D3 — In-memory vs durable bus persistence
- D4 — Hexagonal (ports & adapters) module layout

**Evidence signals (heuristic — verify before acting):**
- code paths referenced — the review covers document + code decisions

**Design moves to test:**
- Can this be a module inside the current deployable before it becomes a service?
- Which dependency can be inverted so the core owns the interface?
- What is the smallest reversible step that tests the boundary?
- Which invariant spans more than one aggregate, and does the transaction span it too?
- Can the write model be separated from read shapes without splitting the database?
- What is the migration and rollback path for existing data?
- Invert a dependency so the unstable thing depends on the stable thing.
- Make an implicit boundary or invariant explicit before adding mechanism.
- Shrink the decision: can half of it ship independently and reversibly?

**Challenge questions:**
(see full challenge_decision brief — six lenses: Problem & forces, Alternatives & tradeoffs, Domain fit (DDD), Architecture & boundaries, Testable design, Craftsmanship)

## Scorecard (agent fills; 1 = poor, 5 = strong, evidence required)

| Lens | Score | Evidence (file:line, test, benchmark) | Action |
|------|-------|----------------------------------------|--------|
| Problem & forces | 4 | SPEC.md:7-14 — problem, users, outcome hypothesis stated | none |
| Alternatives & tradeoffs | 5 | SPEC.md:43-100 — each decision lists 2+ credible alternatives incl. simplest | none |
| Domain fit (DDD) | 4 | SPEC.md:56-70 — aggregate (telemetry event), invariant (per-device ordering), boundary | none |
| Architecture & boundaries | 5 | SPEC.md:96-116 — hexagonal, stateless, ports/adapters, core owns interface | none |
| Testable design | 4 | SPEC.md:40-43 — domain core imports no framework; tests written in wave 1 | none |
| Craftsmanship | 4 | SPEC.md:56-116 — reversible steps, domain names, typed errors | none |
| Decision record | 5 | SPEC.md:43-116 — context, decision, alternatives, consequences, reversibility all present | none |

## Verdict (agent fills)

```
VERDICT: ACCEPT
STEELMAN: Stateless ingestion service on Kafka with event sourcing — any instance accepts any device's events, per-device ordering via Kafka partition key, immutable append-only facts replayable by the consumer. Hexagonal core keeps business rules framework-free and fast to test.
SMALLEST NEXT STEP: Implement wave 1 — ingest domain core (accept/validate/order/append) + Kafka bus adapter + HTTP ingestion adapter, with one acceptance test per AC.
REVISIT TRIGGER: per-device ordering latency or ingestion throughput hits a bottleneck, or a second writer to the same event stream is needed.
```