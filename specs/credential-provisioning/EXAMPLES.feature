# credential-provisioning — specifications by example
# Scenario tags @w<N> map items to delivery waves (see WAVES.md / BACKLOG.md).

Feature: credential-provisioning

  @w1 @happy-path
  Scenario: a credential can be provisioned for a registered device via API
    Given a device "device-42" is registered
    When a credential "cred-42" is provisioned for device "device-42" via POST /v1/credentials/provision
    Then the response indicates the credential was provisioned
    And authorizing device "device-42" with credential "cred-42" succeeds

  @w1 @sad-path
  Scenario: provisioning a credential for an unregistered device is rejected
    When a credential "cred-99" is provisioned for device "device-99" via POST /v1/credentials/provision
    Then the response is rejected with a 400 error

  @w2 @happy-path
  Scenario: a revoked credential is rejected for authorization even if previously valid
    Given a credential "cred-42" is provisioned for device "device-42"
    When credential "cred-42" is revoked via POST /v1/credentials/revoke
    Then authorizing device "device-42" with credential "cred-42" is rejected

  @w2 @happy-path
  Scenario: credential rotation invalidates the old credential and activates the new one
    Given a credential "cred-old" is provisioned for device "device-42"
    When credential "cred-old" is rotated to "cred-new" for device "device-42" via POST /v1/credentials/rotate
    Then authorizing device "device-42" with credential "cred-old" is rejected
    And authorizing device "device-42" with credential "cred-new" succeeds
