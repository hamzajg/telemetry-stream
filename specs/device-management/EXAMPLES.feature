# device-management — specifications by example
# Scenario tags @w<N> map items to delivery waves (see WAVES.md / BACKLOG.md).

Feature: device-management

  @w1 @happy-path
  Scenario: registered device is provisioned with credentials and can produce telemetry
    Given a device "device-42" is registered
    When credentials are provisioned for device "device-42"
    Then device "device-42" is authorized to produce telemetry
    And credentials are returned for device "device-42"

  @w2 @sad-path
  Scenario: unregistered device is rejected and cannot produce telemetry
    Given device "device-999" is not registered
    When a credential for device "device-999" is presented
    Then device "device-999" is not authorized to produce telemetry

  @w2 @sad-path
  Scenario: revoked credential is rejected even if previously valid
    Given device "device-42" is registered with credential "key-1"
    When credential "key-1" is revoked
    Then credential "key-1" is not valid
    And device "device-42" is not authorized to produce telemetry with "key-1"

  @w2
  Scenario: credential rotation invalidates old credential and activates new one
    Given device "device-42" is registered with credential "key-1"
    When credential "key-2" is rotated in for device "device-42"
    Then credential "key-1" is not valid
    And credential "key-2" is valid
    And device "device-42" is authorized to produce telemetry with "key-2"

  @w2
  Scenario: device registry is queryable — active device count and registration details
    Given devices "device-42" and "device-99" are registered
    When the registry is queried for active device count
    Then the count is 2
    And registration details for device "device-42" are returned
