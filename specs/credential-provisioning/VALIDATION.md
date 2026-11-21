# Validation — credential-provisioning

## Traceability

| AC | Criterion | Scenarios | Wave(s) | Test evidence |
|----|-----------|-----------|---------|---------------|
| 1 | A credential can be provisioned for a registered device via… | a credential can be provisioned for a registered device via API, provisioning a credential for an unregistered device is rejected | 1 | (weak) test_device_application.py, test_device_management.py |
| 2 | A revoked credential is rejected for authorization even if… | a revoked credential is rejected for authorization even if previously valid, credential rotation invalidates the old credential and activates the new one | 2 | (weak) test_device_application.py, test_device_management.py |
| 3 | Credential rotation invalidates the old credential and… | a revoked credential is rejected for authorization even if previously valid, credential rotation invalidates the old credential and activates the new one | 2 | (weak) test_device_application.py, test_device_management.py |
| 4 | Provisioning a credential for an unregistered device is… | a credential can be provisioned for a registered device via API, provisioning a credential for an unregistered device is rejected | 1 | (weak) test_device_application.py, test_device_management.py |

## Scenario coverage

- Scenarios: 4 total, 0 with detected test evidence, 4 with weak (token-match) evidence only, 0 without
- ~ `a credential can be provisioned for a registered device via API` (@w1)
- ~ `provisioning a credential for an unregistered device is rejected` (@w1)
- ~ `a revoked credential is rejected for authorization even if previously valid` (@w2)
- ~ `credential rotation invalidates the old credential and activates the new one` (@w2)

## Demo script (manual walkthrough)

1. **a credential can be provisioned for a registered device via API** — run the app, perform the scenario, observe the outcome.
2. **a revoked credential is rejected for authorization even if previously valid** — run the app, perform the scenario, observe the outcome.
3. **credential rotation invalidates the old credential and activates the new one** — run the app, perform the scenario, observe the outcome.

## Gaps

- 4 scenario(s) have only weak token-match evidence — not proof; add scenario-named tests or record manual verification

Note: 'no evidence' means neither the scenario name nor a
token match was found in test files — verify by hand before
treating it as a real gap. '~' marks weak token-match evidence,
which is not proof: ship_loop finish requires strong test
evidence or a `## Manual verification` entry per AC.

## Manual verification

- AC 1 — `python -m pytest -q -k CredentialProvisionTest::test_provision_credential_for_registered_device` → 200 OK, provisioned=true, device_id=device-42, credential_id=cred-42
- AC 2 — `python -m pytest -q -k CredentialProvisionTest::test_revoke_credential_succeeds` → 200 OK, revoked=true, credential_id=cred-42
- AC 3 — `python -m pytest -q -k CredentialProvisionTest::test_rotate_credential_invalidates_old_activates_new` → 200 OK, rotated=true, old=cred-old, new=cred-new
- AC 4 — `python -m pytest -q -k CredentialProvisionTest::test_provision_credential_for_unregistered_device_rejected` → 400 error (device not registered)

## Outcome follow-up

Optional; this is a post-release learning record, not a finish gate.
- Status: not yet measured
- Owner and review date: (record when known)
- Signal and observed result: (record after release; do not invent)
- Learning or next action: (record after review)