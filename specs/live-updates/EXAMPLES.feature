# live-updates — specifications by example
# Scenario tags @w<N> map items to delivery waves (see WAVES.md / BACKLOG.md).

Feature: live-updates

  @w1 @happy-path
  Scenario: newly ingested event is pushed to all connected WebSocket clients
    Given the frontend is connected to /v1/ws/telemetry
    When a telemetry event is ingested via POST /v1/telemetry
    Then the WebSocket client receives the event as a JSON message
    And every other connected WebSocket client receives the same event

  @w1
  Scenario: frontend opens WebSocket on dashboard load and displays live events
    Given the dashboard page loads
    When a WebSocket connection is established to /v1/ws/telemetry
    Then incoming events are appended to the telemetry table without reload

  @w2 @sad-path
  Scenario: WebSocket disconnect does not lose previously loaded events
    Given the dashboard displays previously loaded telemetry events
    When the WebSocket connection closes
    Then the previously loaded events remain visible
    And the dashboard can reconnect and resume receiving live events
