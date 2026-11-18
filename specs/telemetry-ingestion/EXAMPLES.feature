# telemetry-ingestion — specifications by example
# Scenario tags @w<N> map items to delivery waves (see WAVES.md / BACKLOG.md).

Feature: telemetry-ingestion

  @w1 @happy-path
  Scenario: valid telemetry event is accepted with a per-device offset
    Given a registered device "device-42"
    When a valid telemetry event is emitted for device "device-42" at sequence 1
    Then the event is accepted
    And the event is assigned offset 1 for device "device-42"

  @w2
  Scenario: events for the same device are delivered in emission order
    Given a registered device "device-42"
    When telemetry events are emitted for device "device-42" at sequence 1, 2, 3
    Then the consumer reads events for device "device-42" in order 1, 2, 3

  @w1 @sad-path
  Scenario: event failing schema validation is rejected and not persisted
    Given a registered device "device-42"
    When a telemetry event with an invalid schema is emitted for device "device-42"
    Then the event is rejected with error "invalid_schema"
    And the event is not persisted for device "device-42"

  @w2
  Scenario: any ingestion instance can accept events for any device
    Given two ingestion instances "instance-a" and "instance-b"
    When a telemetry event is emitted for device "device-42" to instance-a
    Then instance-a accepts the event
    And a subsequent event for device "device-42" may be accepted by instance-b

  @w3
  Scenario: stored events are replayable from a bus offset
    Given telemetry events persisted for device "device-42" at offsets 1..5
    When the consumer requests events for device "device-42" from offset 3
    Then the consumer receives events at offsets 3, 4, 5
