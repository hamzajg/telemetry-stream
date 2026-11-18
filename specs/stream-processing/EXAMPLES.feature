# stream-processing — specifications by example
# Scenario tags @w<N> map items to delivery waves (see WAVES.md / BACKLOG.md).

Feature: stream-processing

  @w1 @happy-path
  Scenario: consumed telemetry event updates current device state
    Given a telemetry event for device "device-42" at sequence 1
    When the stream processor consumes the event
    Then current state for device "device-42" reflects sequence 1
    And the projection stores the latest reading

  @w2
  Scenario: consumer reads events in per-device emission order from Kafka
    Given telemetry events for device "device-42" at sequence 1, 2, 3 in Kafka
    When the stream processor consumes them
    Then the projection for device "device-42" ends at sequence 3
    And intermediate states 1, 2, 3 were applied in order

  @w1 @sad-path
  Schema validation: event failing schema is skipped and not projected
    Given a telemetry event with an invalid schema for device "device-42"
    When the stream processor consumes it
    Then the event is not projected for device "device-42"
    And a projection error is counted

  @w2
  Scenario: consumer is stateless across restarts
    Given the stream processor projects state then restarts
    When it resumes from the last committed Kafka offset
    Then projection rebuilds from that offset without duplicating events

  @w3
  Scenario: stored events are replayable from a bus offset
    Given telemetry events persisted for device "device-42" at offsets 1..5
    When the consumer requests events for device "device-42" from offset 3
    Then the consumer receives events at offsets 3, 4, 5
