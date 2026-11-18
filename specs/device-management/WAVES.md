# Waves — device-management

Each wave IS an iteration: a time-boxed, independently shippable
increment — one branch, one PR, green tests, demoable outcome.
Do not start wave N+1 until wave N merges.

## Wave 1 — iteration 1

Scenarios proven by this wave:
- registered device is provisioned with credentials and can produce telemetry

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US1 | As a device operator, I want to register a device and provision its credentials, so that I can deploy it to produce telemetry | M | — | device registration + credential provisioning |

## Wave 2 — iteration 2

Scenarios proven by this wave:
- unregistered device is rejected and cannot produce telemetry
- revoked credential is rejected even if previously valid
- credential rotation invalidates old credential and activates new one
- device registry is queryable — active device count and registration details

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US2 | As a platform operator, I want unregistered devices rejected, so that rogue devices cannot inject bad data | S | US1 | allowlist authorization |
| US3 | As a security officer, I want to revoke a compromised credential, so that it is rejected even if previously valid | S | US1 | credential revocation |
| US4 | As a platform operator, I want to rotate credentials, so that the old credential is invalidated and the new one activated | S | US1 | credential rotation |
| US5 | As a platform operator, I want to query the device registry for active device count and registration details, so that I can audit the fleet | S | US1 | registry query |

## Wave 3 — iteration 3

Scenarios proven by this wave:
- production infra adapters wired (env-var credential store, no in-memory doubles)

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US6 | As a platform operator, I want credentials provisioned via environment variables, so that the system runs without in-memory doubles in production | S | US2 | env-var CredentialStore adapter |
