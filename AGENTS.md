# AGENTS.md — telemetry-stream

Product repo for Telemetry Stream. Managed by OpenHarness.

## Stack

Not yet chosen. Record the backend/frontend selection and a one-line
justification as an ADR/decision in the first feature spec (`SPEC.md →
## Decisions`).

## Delivery loop

Product work flows through `specs/<feature>/` and the `/ship-loop` delivery
loop (see OpenHarness `SELF/PRINCIPLES.md` D001–D014). One wave = one branch =
one PR. Default merge policy is `review` (PRs stay open for review).

## Checkpoints before code

1. Fill `SPEC.md` (problem/users/scope/acceptance criteria), write Gherkin
   scenarios in `EXAMPLES.feature` with `@w<N>` tags, add backlog items to
   `BACKLOG.md`, and define preconditions in `GATES.md`.
2. Record architecture decisions in `SPEC.md → ## Decisions` (persistence
   model, consistency, module boundaries, stateless vs stateful).
3. Run `/challenge-decision` and record gate G1 met
   (`specs/<feature>/DECISION-REVIEW.md`).
4. Run `review_delivery --phase=spec --write` and have the
   `delivery-auditor` fill `AUDIT: PASS|CONCERNS|BLOCK` in
   `SPEC-AUDIT.md`.
5. Only then run `wave_plan` and `ship_loop --action=start --wave=1`.

## Repo rules

- No secrets or credentials in code; environment variables or placeholders only.
- No framework leakage into domain modules.
- Design decisions recorded in SPEC.md and challenged before wave planning.
- Specs and deliveries independently audited before planning and before finish.
