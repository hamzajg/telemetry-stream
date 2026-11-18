# Validation — device-management

## Traceability

| AC | Criterion | Scenarios | Wave(s) | Test evidence |
|----|-----------|-----------|---------|---------------|
| 1 | A registered device is provisioned with credentials and can… | registered device is provisioned with credentials and can produce telemetry | 1 | test_device_management.py |
| 2 | An unregistered device is rejected and cannot produce… | registered device is provisioned with credentials and can produce telemetry | 1 | test_device_management.py |
| 3 | A revoked credential is rejected even if previously valid | registered device is provisioned with credentials and can produce telemetry | 1 | test_device_management.py |
| 4 | Credential rotation invalidates the old credential and… | registered device is provisioned with credentials and can produce telemetry | 1 | test_device_management.py |
| 5 | Device registry is queryable: active device count and… | registered device is provisioned with credentials and can produce telemetry | 1 | test_device_management.py |
| 6 | Credentials are loadable from environment variables | credentials are loaded from environment variables | 3 | test_env_var_credential_store.py |

## Scenario coverage

- Scenarios: 6 total, 6 with detected test evidence, 0 without
- ✓ `registered device is provisioned with credentials and can produce telemetry` (@w1)
- ✓ `unregistered device is rejected and cannot produce telemetry` (@w2)
- ✓ `revoked credential is rejected even if previously valid` (@w2)
- ✓ `credential rotation invalidates old credential and activates new one` (@w2)
- ✓ `device registry is queryable — active device count and registration details` (@w2)
- ✓ `credentials are loaded from environment variables` (@w3)

## Demo script (manual walkthrough)

1. **registered device is provisioned with credentials and can produce telemetry** — run the app, perform the scenario, observe the outcome.

## Gaps

- none — spec is fully traced

Note: 'no evidence' means neither the scenario name nor a
token match was found in test files — verify by hand before
treating it as a real gap. '~' marks weak token-match evidence.

## Outcome follow-up

Optional; this is a post-release learning record, not a finish gate.
- Status: not yet measured
- Owner and review date: (record when known)
- Signal and observed result: (record after release; do not invent)
- Learning or next action: (record after review)