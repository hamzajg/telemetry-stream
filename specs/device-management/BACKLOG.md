# Backlog: device-management

Items are USER STORIES in the parseable format below — keep the heading
shape `## US<n> — <story>` and the field lines intact so `wave_plan` can
parse them. Write the story as: "As a <role>, I want <goal>, so that
<value>" — the title after the dash IS the story.

## US1 — As a device operator, I want to register a device and provision its credentials, so that I can deploy it to produce telemetry
- Scenarios: @w1
- Size: M
- Notes: device registration + credential provisioning

## US2 — As a platform operator, I want unregistered devices rejected, so that rogue devices cannot inject bad data
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: allowlist authorization

## US3 — As a security officer, I want to revoke a compromised credential, so that it is rejected even if previously valid
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: credential revocation

## US4 — As a platform operator, I want to rotate credentials, so that the old credential is invalidated and the new one activated
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: credential rotation

## US5 — As a platform operator, I want to query the device registry for active device count and registration details, so that I can audit the fleet
- Scenarios: @w2
- Depends: US1
- Size: S
- Notes: registry query

Order stories by user value; dependencies express technical order only.
