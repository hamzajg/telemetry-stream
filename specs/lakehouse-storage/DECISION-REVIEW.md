# Decision review brief — Spec: lakehouse-storage

- Source: `specs/lakehouse-storage/SPEC.md (## Decisions)`
- Generated: 2026-11-18T05:32:32Z
- Detected type: data, architecture
- Readiness: **CHALLENGE** (6/6 record elements)
- This brief is input to judgment, not a verdict. The agent fills the scorecard after reading the code.

**Reversibility:** stated

**Alternatives on record (verify they are credible, not strawmen):**
- ### D1 — Stateless
- stateful lakehouse writer
- A stateless writer (any instance writes any device) with idempotent writes is trivial to restart and scale. - Options considered: 1.
- ### D2 — Storage format: Parquet

## Evidence signals (heuristic — verify before acting)

- no code paths referenced — the review is document-only

## Design moves to test

- Which invariant spans more than one aggregate, and does the transaction span it too?
- Can the write model be separated from read shapes without splitting the database?
- What is the migration and rollback path for existing data?
- Can this be a module inside the current deployable before it becomes a service?
- Which dependency can be inverted so the core owns the interface?
- What is the smallest reversible step that tests the boundary?
- Invert a dependency so the unstable thing depends on the stable thing.
- Make an implicit boundary or invariant explicit before adding mechanism.
- Shrink the decision: can half of it ship independently and reversibly?

## Challenge questions

### 1. Problem & forces
- What user/business outcome does this serve, and what breaks if we do nothing?
- Which quality attributes actually drive it (correctness, latency, cost, operability, compliance, time-to-market)? Rank them.
- Which constraints are fixed (budget, deadline, team, contracts) and which are assumed?
- Who owns this decision, and who must live with the consequences?
**Good looks like:** The dominant force is named, and "do nothing" is treated as a real option.

### 2. Alternatives & tradeoffs
- What are at least two credible alternatives, including the simplest thing that could work?
- For each: what does it make easy, what does it make hard, and what does it cost to reverse?
- Is this a one-way or two-way door? If one-way, what evidence justifies it?
- What would have to be true for the chosen option to be wrong?
**Good looks like:** A tradeoff matrix names winners and losers; reversibility is explicit; no strawman options.

### 3. Domain fit (DDD)
- Which bounded context owns this concept, and is the boundary drawn around language or deployment?
- Which terms are overloaded across contexts, and where is the translation (anti-corruption layer)?
- What are the aggregates, their invariants, and the transaction boundary? Does one transaction span aggregates?
- Are domain events the right integration mechanism, or is this a synchronous dependency?
- Does the model carry behavior, or is it an anemic data bag?
- Which consistency guarantee is required, and which can be eventual?
**Good looks like:** Ubiquitous language is explicit, invariants are protected at the boundary, external models are translated.

### 4. Architecture & boundaries
- Which direction do dependencies point? Can the core be tested without the framework, DB, or network?
- What is the smallest boundary that isolates this change (module, port, package)?
- What happens when each external dependency is slow, down, or returns garbage?
- Where does data ownership live, and is there a second writer?
- What is the operational story: config, migrations, rollout, rollback, observability?
**Good looks like:** Policy depends on nothing; mechanisms are adapters; failure and migration paths are named.

### 5. Testable design
- Where are the seams? Can time, randomness, IO, and external calls be injected?
- Which behaviors get fast unit tests, which need integration, which need contract tests?
- Does each acceptance criterion map to an observable check, or only to implementation details?
- Are the tests deterministic and independent (no shared state, no sleeps)?
- What is the failure signal when this decision turns out wrong in production?
**Good looks like:** Behavior-first tests, deterministic seams, scenario-to-test traceability, a named failure signal.

### 6. Craftsmanship
- Is this the smallest reversible step, or a big-bang change?
- Are names from the domain, or from the framework/table?
- Is the error model explicit (typed failures vs exceptions vs silent nulls)?
- Is there speculative abstraction (interfaces with one implementation, config nobody sets)?
- Is the migration path documented and rollback-able?
**Good looks like:** Small steps, intention-revealing names, explicit errors, no speculative generality, documented migration.

### 7. Decision record
- Are status, owner, and date recorded?
- Are consequences (positive and negative) written down?
- Is there a revisit trigger (metric, date, event)?
- Are links to evidence, code, and related ADRs present?
**Good looks like:** A future reader can tell why, what was traded, and when to revisit.

## Scorecard (agent fills; 1 = poor, 5 = strong, evidence required)

| Lens | Score | Evidence (file:line, test, benchmark) | Action |
|------|-------|----------------------------------------|--------|
| Problem & forces | 4 | SPEC.md:7-14 — problem, users, outcome hypothesis stated | none |
| Alternatives & tradeoffs | 5 | SPEC.md:56-116 — each decision lists 2+ credible alternatives incl. simplest | none |
| Domain fit (DDD) | 4 | SPEC.md:86-98 — aggregate (lakehouse row), invariant (idempotency by offset), boundary | none |
| Architecture & boundaries | 5 | SPEC.md:104-116 — hexagonal, stateless, ports/adapters, core owns interface | none |
| Testable design | 4 | SPEC.md:40-43 — domain core imports no framework; no tests written yet | write domain-core unit tests in wave 1 |
| Craftsmanship | 4 | SPEC.md:56-116 — reversible steps, domain names, typed errors | none |
| Decision record | 5 | SPEC.md:56-116 — context, decision, alternatives, consequences, reversibility all present | none |

## Verdict (agent fills)

```
VERDICT: ACCEPT
STEELMAN: Stateless lakehouse writer on S3 + Parquet — any instance writes any device, idempotent writes keyed by device_id + offset, Parquet columnar format queryable by Glue/Athena. Hexagonal core keeps business rules framework-free and fast to test.
SMALLEST NEXT STEP: Implement wave 1 — lakehouse domain core (write/partition/idempotency) + local filesystem adapter (S3 double) + Glue catalog stub, with one acceptance test per AC.
REVISIT TRIGGER: lakehouse lag or write throughput hits a bottleneck, or exactly-once semantics beyond idempotent offset writes is needed.
```

Run the review with `/challenge-decision` and the `decision-challenger`
subagent. It is advisory: it never blocks a gate or a merge.
