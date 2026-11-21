# Waves — credential-provisioning

Each wave IS an iteration: a time-boxed, independently shippable
increment — one branch, one PR, green tests, demoable outcome.
Do not start wave N+1 until wave N merges.

## Wave 1 — iteration 1

Scenarios proven by this wave:
- a credential can be provisioned for a registered device via API
- provisioning a credential for an unregistered device is rejected

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US1 | As a device operator, I want to provision a credential for a registered device via API, so that the device can authenticate and produce telemetry | M | — | POST /v1/credentials/provision; writable EnvVarCredentialStore.save |
| US4 | As a security officer, I want provisioning a credential for an unregistered device to be rejected, so that only registered devices receive credentials | S | — | 400 error when device not registered |

## Wave 2 — iteration 2

Scenarios proven by this wave:
- a revoked credential is rejected for authorization even if previously valid
- credential rotation invalidates the old credential and activates the new one

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US2 | As a platform operator, I want to revoke a credential via API, so that a compromised credential is rejected immediately | S | US1 | POST /v1/credentials/revoke |
| US3 | As a platform operator, I want to rotate a credential via API, so that the old credential is invalidated and the new one activated | S | US1 | POST /v1/credentials/rotate |
