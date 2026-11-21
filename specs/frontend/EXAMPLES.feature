# frontend — specifications by example
# Scenario tags @w<N> map items to delivery waves (see WAVES.md / BACKLOG.md).

Feature: frontend

  @w1 @happy-path
  Scenario: dashboard loads and displays live telemetry events
    Given the frontend dev server is running
    When the operator opens the dashboard
    Then the page loads without errors
    And telemetry events from the backend are displayed

  @w2
  Scenario: operator filters telemetry by device id
    Given telemetry events are displayed for multiple devices
    When the operator enters device id "device-42" in the filter
    Then only events for device "device-42" are shown

  @w2 @sad-path
  Scenario: emergency-incident events surface as incidents
    Given an emergency-incident telemetry event is ingested
    When the dashboard refreshes
    Then the incident is listed with severity and timestamp

  @w2
  Scenario: device registry shows active count and registration details
    Given registered devices exist in the backend
    When the operator opens the device registry view
    Then the active device count is displayed
    And registration details for each device are shown

  @w3
  Scenario: observability panel shows accept/reject counters and consumer lag
    Given the ingestion backend has processed events
    When the operator opens the observability panel
    Then accept and reject counters are displayed
    And consumer lag is displayed
