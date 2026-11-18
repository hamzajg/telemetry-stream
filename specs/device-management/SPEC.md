# Spec: device-management

> Spec-driven development artifact. This file is the contract: implementation
> is done when every acceptance criterion maps to a scenario in
> `EXAMPLES.feature` and every scenario has a passing check.

## Problem

Telemetry producers and stream consumers authenticate to the Kafka bus and
lakehouse with no credential management. Any client can produce to any device
topic, and there is no device registry to track which devices are authorized
to emit telemetry. This means rogue devices can inject bad data, and there is
no revocation path for compromised credentials.

## Users

- Device operator — registers field devices and provisions their credentials
  before deployment.
- Platform operator — rotates and revokes credentials, audits device
  registrations, and enforces per-device authorization.
- Security officer — reviews which devices are active and which credentials
  have been revoked.

## Outcome hypothesis

- Expected user outcome: only registered devices with valid credentials can
  produce telemetry; revoked credentials are rejected immediately.
- Opportunity evidence: assumption — sourced from the library course section
  titles (Setting up and AWS secret key and access key); not yet validated
  against production requirements.
- Signal: registration count, credential rotation interval, rejected
  unauthorized producers, revoked credential count (baseline unknown; do not
  invent targets).
- Follow-up owner/date: platform operator — review after wave 1 ships.

## Scope (in)

- `device` domain: register devices, provision credentials, enforce
  per-device authorization, revoke credentials.
- `credential` domain: generate, rotate, and revoke API keys/secrets.
- `authorization` domain: check whether a device/credential may produce to a
  given topic.
- `registry` adapter: device registry store (in-memory in wave 1, swappable
  for a DB).
- `secret` adapter: credential store (environment variables/placeholders in
  wave 1, swappable for a secret manager).
- Observability: registration count, active credentials, revoked
  credentials, authz accept/reject rates.

## Scope (out)

- Credential distribution to devices (out-of-band) — later feature.
- Hardware security module (HSM) integration — later feature.
- OAuth2 / OIDC integration — later feature.
- Device telemetry ingestion itself — earlier feature (telemetry-ingestion).
- Web UI / dashboards — later feature.

## Acceptance criteria

<!-- Scenario(s): use scenario names verbatim from EXAMPLES.feature and/or
     @w<N> tags — ship_validate resolves both for traceability. -->

| # | Criterion | Scenario(s) |
|---|-----------|-------------|
| 1 | A registered device is provisioned with credentials and can produce telemetry | @w1 |
| 2 | An unregistered device is rejected and cannot produce telemetry | @w1 |
| 3 | A revoked credential is rejected even if previously valid | @w1 |
| 4 | Credential rotation invalidates the old credential and activates the new one | @w1 |
| 5 | Device registry is queryable: active device count and registration details | @w1 |
| 6 | Credentials are loadable from environment variables | @w3 |

## Decisions

### D1 — Stateless vs stateful device registry

- Context & forces: The device registry must track registered devices and
  their credentials. A stateful registry pins lookups to instances and
  complicates restarts. A stateless registry (any instance can look up any
  device) with a shared backing store is trivial to restart and scale.
- Options considered:
  1. Stateful, device-affinity registry instances (complex restarts, slot
     pinning).
  2. Stateless registry backed by a shared store (any instance looks up any
     device, simple restart).
- Decision & why: Stateless registry. The backing store (in-memory in wave
  1, swappable for a DB) holds device state; the service holds none, so any
  instance can serve any lookup and instances are interchangeable.
- Consequences:
  - Positive: horizontal scale, simple restarts, no instance pinning.
  - Negative: backing store is a single point of read; eventual consistency
    if replicated later.
- Reversibility: two-way door — adding instance affinity later is a config
  change.

### D2 — Credential storage: environment variables vs secret manager

- Context & forces: Credentials must be stored securely and retrievable for
  validation. Environment variables are simple but not rotatable without
  redeploy. A secret manager is secure and rotatable but adds ops.
- Options considered:
  1. Environment variables / placeholders (simple, zero ops, not rotatable
     without redeploy — acceptable for wave 1 local dev).
  2. Secret manager (AWS Secrets Manager, secure, rotatable, ops overhead).
- Decision & why: Environment variables / placeholders for wave 1. Secrets
  must never be hard-coded (library rules); env vars satisfy local dev and
  the adapter is swappable for a secret manager later.
- Consequences:
  - Positive: zero ops, simple, no secrets in code.
  - Negative: rotation requires redeploy in wave 1; no audit log of access.
- Reversibility: two-way door behind an adapter — swapping to a secret
  manager is an adapter change.

### D3 — Authorization model: allowlist vs denylist

- Context & forces: The service must decide whether a device/credential may
  produce to a topic. An allowlist (only registered devices may produce) is
  secure by default. A denylist (block known-bad devices) is permissive by
  default and unsafe.
- Options considered:
  1. Allowlist: only registered, active devices may produce (secure by
     default).
  2. Denylist: block known-bad devices, allow everything else (permissive,
     unsafe).
- Decision & why: Allowlist. Zero trust — only registered devices with valid
  credentials may produce. Everything else is rejected by default.
- Consequences:
  - Positive: secure by default, simple logic, easy to audit.
  - Negative: new devices must be registered before producing (operational
    step).
- Reversibility: one-way door for the security posture — moving to denylist
  would weaken security and require a deliberate decision.

### D4 — Module layout: hexagonal (ports & adapters)

- Context & forces: The device/credential/authorization domain must be
  testable without a database, secret manager, or cloud SDK.
- Options considered:
  1. Layered with DB/SDK imports in the domain (simple, domain depends on
     infrastructure).
  2. Hexagonal: domain core depends on nothing; ports define interfaces;
     adapters implement registry, secret store (more files, domain is pure
     and fast to test).
- Decision & why: Hexagonal (ports & adapters). Domain core imports no
  database, secret SDK, or HTTP library.
- Consequences:
  - Positive: domain core tests run without DB/secret manager; adapters
    swappable/stubbed; local-first dev.
  - Negative: more abstractions up front.
- Reversibility: two-way door.

## Stack decision

- Backend: Python (stdlib-first domain core).
  Justification: domain core stays framework-free; adapters for DB/secret
  manager are swappable; consistent with ingestion/stream/lakehouse.
- Registry store: in-memory dict (wave 1), swappable for a database.
- Secret store: environment variables / placeholders (wave 1), swappable for
  AWS Secrets Manager.
