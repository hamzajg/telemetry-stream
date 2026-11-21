# Spec: credential-provisioning

> Spec-driven development artifact. This file is the contract: implementation
> is done when every acceptance criterion maps to a scenario in
> `EXAMPLES.feature` and every scenario has a passing check.

## Problem

Device credentials are read-only: `EnvVarCredentialStore.save` raises
`NotImplementedError`, so operators cannot provision, revoke, or rotate
credentials through the API. Any device registration via
`POST /v1/devices/register` can register a device, but there is no way to
issue it a credential to authenticate with the bus. Without writable
credential storage and HTTP endpoints, credentials cannot be managed at
runtime — only out-of-band via environment variables before deploy.

## Users

- Device operator — provisions credentials for newly registered field
  devices so they can authenticate and produce telemetry.
- Platform operator — revokes compromised credentials and rotates stale
  ones without redeploying.
- Security officer — audits which credentials are active vs revoked.

## Outcome hypothesis

- Expected user outcome: a registered device can be issued a credential
  via API, a revoked credential is rejected immediately, and rotation
  invalidates the old credential while activating the new one — all
  without a redeploy.
- Opportunity evidence: assumption — sourced from the env_var_credential_store
  `NotImplementedError` (read-only placeholder) and the device-management
  spec decision D2 (env vars / placeholders swappable for a secret manager).
  Not yet validated against production requirements.
- Signal: credentials provisioned count, revoked count, rotation count,
  rejected unauthorized producers (baseline unknown; do not invent targets).
- Follow-up owner/date: platform operator — review after wave 1 ships.

## Scope (in)

- `credential` domain: make `CredentialStore.save` writable so credentials
  can be inserted/replaced at runtime.
- `credential` application: expose provision, revoke, and rotate use cases
  through `CredentialApplication` (already exists) via HTTP.
- HTTP adapter: add `POST /v1/credentials/provision`,
  `POST /v1/credentials/revoke`, `POST /v1/credentials/rotate` endpoints,
  wired to `CredentialApplication`.
- Secret store: `EnvVarCredentialStore.save` no longer raises
  `NotImplementedError`; persists credentials in memory (wave 1),
  swappable for a secret manager later.
- Observability: credentials provisioned/revoked/rotated counts.

## Scope (out)

- Credential distribution to devices (out-of-band) — later feature.
- Hardware security module (HSM) integration — later feature.
- OAuth2 / OIDC integration — later feature.
- Device telemetry ingestion itself — earlier feature (telemetry-ingestion).
- Web UI / dashboards — later feature.
- Persistent credential store (database) — wave 1 uses in-memory; DB swap
  is a later adapter change.

## Acceptance criteria

| # | Criterion | Scenario(s) |
|---|-----------|-------------|
| 1 | A credential can be provisioned for a registered device via API | @w1 |
| 2 | A revoked credential is rejected for authorization even if previously valid | @w2 |
| 3 | Credential rotation invalidates the old credential and activates the new one | @w2 |
| 4 | Provisioning a credential for an unregistered device is rejected | @w1 |

## Decisions

### D1 — Credential storage: writable in-memory store vs secret manager

- Context & forces: Credentials must be writable at runtime (save/revoke/
  rotate). Environment variables are simple but not writable without
  redeploy. A secret manager is secure and rotatable but adds ops.
- Options considered:
  1. Writable in-memory `CredentialStore` adapter (simple, zero ops, lost on
     restart — acceptable for wave 1 local dev).
  2. Secret manager (AWS Secrets Manager, secure, rotatable, ops overhead).
- Decision & why: Writable in-memory store for wave 1. Secrets must never
  be hard-coded (library rules); the adapter is swappable for a secret
  manager later behind the `CredentialStore` port.
- Consequences:
  - Positive: zero ops, simple, writable at runtime, testable without
    cloud SDK.
  - Negative: credentials lost on restart; no audit log of access.
- Reversibility: two-way door behind an adapter — swapping to a secret
  manager is an adapter change.

### D2 — HTTP endpoint shape: provision/revoke/rotate as separate endpoints

- Context & forces: The domain already models provision, revoke, and rotate
  as separate commands. The HTTP surface should mirror them so each action
  has its own contract, status code, and error handling.
- Options considered:
  1. Separate endpoints per action (`POST /v1/credentials/provision`,
     `/revoke`, `/rotate`) — clear contracts, easy to test.
  2. Single `POST /v1/credentials` with an `action` field — one endpoint,
     ambiguous error semantics.
- Decision & why: Separate endpoints. Each action has distinct preconditions
  (provision needs a registered device; revoke/rotate need an existing
  credential) and distinct failure modes.
- Consequences:
  - Positive: clear contracts, distinct status codes, simple routing.
  - Negative: three endpoints instead of one.
- Reversibility: two-way door — consolidating later is a routing change.

## Stack decision

- Backend: Python (stdlib-first domain core, FastAPI HTTP adapter).
  Justification: consistent with ingestion/device/lakehouse features;
  domain core stays framework-free; adapters swappable.
- Credential store: in-memory dict (wave 1), swappable for secret manager.
- Wiring: `CredentialApplication` exposed via `create_app` `credential_app`
  parameter.
