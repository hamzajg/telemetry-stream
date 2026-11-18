# lakehouse-storage — specifications by example
# Scenario tags @w<N> map items to delivery waves (see WAVES.md / BACKLOG.md).

Feature: lakehouse-storage

  @w1 @happy-path
  Scenario: projected telemetry event is written to lakehouse partitioned by device_id and date
    Given a projected telemetry event for device "device-42" at sequence 1
    When the lakehouse writer writes the event
    Then the event is stored under device_id="device-42" and event date
    And the stored row matches the projected state

  @w2
  Scenario: lakehouse writes are idempotent — replaying same offset does not duplicate
    Given a projected telemetry event for device "device-42" at sequence 1 offset 10
    When the lakehouse writer writes the event twice with the same offset
    Then exactly one row exists for device "device-42" offset 10

  @w2 @sad-path
  Schema validation: event failing schema is not written to lakehouse
    Given a projected telemetry event with an invalid schema for device "device-42"
    When the lakehouse writer attempts to write it
    Then the event is rejected with error "invalid_schema"
    And no row exists for device "device-42" in the lakehouse

  @w2
  Scenario: lakehouse writer is stateless — any instance can write any device
    Given two lakehouse writer instances "writer-a" and "writer-b"
    When a projected event for device "device-42" is written by writer-a
    Then writer-a accepts the write
    And a subsequent event for device "device-42" may be written by writer-b

  @w3
  Scenario: stored lakehouse rows are recoverable from a committed offset after restart
    Given projected events for device "device-42" at offsets 1..5 written to lakehouse
    When the lakehouse writer restarts from committed offset 3
    Then rows for offsets 3, 4, 5 are recoverable
