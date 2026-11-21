# Decision review brief — Spec: credential-provisioning

- Source: `specs/credential-provisioning/SPEC.md (## Decisions)`
- Generated: 2026-11-21T13:09:43Z
- Detected type: security, api
- Readiness: **CHALLENGE** (6/6 record elements)
- This brief is input to judgment, not a verdict. The agent fills the scorecard after reading the code.

**Reversibility:** stated

**Alternatives on record (verify they are credible, not strawmen):**
- Device operator — provisions credentials for newly registered field devices so they can authenticate and produce telemetry. - Platform operator — revokes compro
- revoked.
- ### D1 — Credential storage: writable in-memory store
- secret manager

## Evidence signals (heuristic — verify before acting)

- no code paths referenced — the review is document-only

## Design moves to test

- What is the threat model, and which asset is actually being protected?
- Where are secrets stored, rotated, and audited?
- What is the least privilege this component needs?
- Is this a public contract or an implementation detail? Who depends on it?
- How will it version, and what is the backward-compatibility promise?
- Are errors part of the contract — consistent shape, codes, retry semantics — or an afterthought?
- Is the contract documented where consumers can find it (OpenAPI, AsyncAPI, schema registry, docs site), and is the doc generated from code or hand-maintained?
- Which fields and operations are stable vs experimental, and what is the deprecation path?
- Is authn/authz explicit per operation with least privilege, and is that visible in the docs?
- Are writes idempotent where clients can retry (idempotency keys, natural keys, upserts)?
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
**Good looks like:** Ubiquitous language is explicit, invariants are protected at the boundary, external models are translated.

### 4. Architecture & boundaries
- Which direction do dependencies point? Can the core be tested without the framework, DB, or network?
- What is the smallest boundary that isolates this change (module, port, package)?
- What happens when each external dependency is slow, down, or returns garbage?
- Where does data ownership live, and is there a second writer?
- What is the operational story: config, migrations, rollout, rollback, observability?
- Who are the consumers, and what is the deprecation policy?
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
| Problem & forces | 4 | SPEC.md:8-13 (read-only NotImplementedError gap), model.py:238-410 (provision/revoke/rotate commands already exist) | none |
| Alternatives & tradeoffs | 4 | SPEC.md:95-116 (D1), SPEC.md:123-141 (D2); in-memory vs secret manager, separate vs single endpoint | none |
| Domain fit (DDD) | 5 | model.py:186-227 (CredentialStore port), model.py:323-362 (rotate_credential domain logic), use_cases.py:179-211 (CredentialApplication) | none |
| Architecture & boundaries | 5 | ports.py:28-35 (CredentialStore protocol), http_adapter.py:315-344 (existing device endpoints as pattern) | none |
| Testable design | 4 | model.py:199-236 (Clock protocol, injectable time seam), existing unit tests stdlib-only | add HTTP adapter tests |
| Craftsmanship | 4 | SPEC.md names match domain (provision/revoke/rotate), error model uses domain exceptions | wire credential_app into create_app |
| Decision record | 4 | SPEC.md:104-152 (D1/D2 with consequences + reversibility), GATES.md:28-39 (G1 defined) | fill verdict below |

## Verdict

```
VERDICT: ACCEPT
STEELMAN: Writable in-memory CredentialStore adapter + separate HTTP endpoints (provision/revoke/rotate) wired to existing CredentialApplication; swap to secret manager later behind the port.
SMALLEST NEXT STEP: Implement EnvVarCredentialStore.save (remove NotImplementedError) and add POST /v1/credentials/provision endpoint.
REVISIT TRIGGER: Credentials lost on restart become a production problem — revisit persistence (DB/secret manager) after wave 1.
```

Run the review with `/challenge-decision` and the `decision-challenger`
subagent. It is advisory: it never blocks a gate or a merge.
