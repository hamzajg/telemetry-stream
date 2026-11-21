# Backlog: credential-provisioning

Items are USER STORIES in the parseable format below — keep the heading
shape `## US<n> — <story>` and the field lines intact so `wave_plan` can
parse them. Write the story as: "As a <role>, I want <goal>, so that
<value>" — the title after the dash IS the story.

## US1 — As a device operator, I want to provision a credential for a registered device via API, so that the device can authenticate and produce telemetry
- Scenarios: @w1
- Size: M
- Notes: POST /v1/credentials/provision; writable EnvVarCredentialStore.save

## US2 — As a platform operator, I want to revoke a credential via API, so that a compromised credential is rejected immediately
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: POST /v1/credentials/revoke

## US3 — As a platform operator, I want to rotate a credential via API, so that the old credential is invalidated and the new one activated
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: POST /v1/credentials/rotate

## US4 — As a security officer, I want provisioning a credential for an unregistered device to be rejected, so that only registered devices receive credentials
- Scenarios: @w1
- Size: S
- Notes: 400 error when device not registered

Order stories by user value; dependencies express technical order only.
