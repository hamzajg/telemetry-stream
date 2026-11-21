# Spec: live-updates

> Spec-driven development artifact. This file is the contract: implementation
> is done when every acceptance criterion maps to a scenario in
> `EXAMPLES.feature` and every scenario has a passing check.

## Problem

The frontend dashboard polls `/v1/telemetry` on a refresh button click, so
operators see stale data until they manually reload. For a real-time streaming
system, operators expect new telemetry events to appear as soon as they are
ingested, without a page refresh.

## Users

- Fleet/operations operator — watches live telemetry and wants new events to
  appear on the dashboard as they arrive.
- Platform operator — observes ingestion health metrics in near real time.

## Outcome hypothesis

- Expected user outcome: new ingested events surface on the dashboard within
  seconds, without manual refresh.
- Opportunity evidence: assumption — sourced from the library course's
  "Realtime Streaming Consumer" theme; not yet validated against production
  telemetry volume.
- Signal: time from ingest to dashboard display (baseline unknown; do not
  invent targets).
- Follow-up owner/date: platform operator — review after wave 1 ships.

## Scope (in)

- WebSocket endpoint `/v1/ws/telemetry` on the FastAPI backend.
- Broadcast newly ingested telemetry events to all connected WebSocket clients
  from the ingestion handler.
- Frontend: open a WebSocket connection on dashboard load and append incoming
  events to the live table without a page reload.
- Keep polling refresh as a fallback for clients that cannot use WebSocket.

### In-scope paths

- `src/telemetry/infrastructure/http_adapter.py` — WebSocket broadcast from ingest handler
- `web/src/App.tsx` — frontend WebSocket client, reconnect, incident highlighting
- `web/src/App.css` — `.ws-status.reconnecting`, `.incident` styles
- `web/src/App.test.tsx` — WebSocket live-updates tests
- `tests/unit/test_http_adapter.py` — backend WebSocket disconnect test
- `evidence/` — tracked evidence bundles committed with each wave
- `.openharness/evidence/` — scratch evidence bundles captured per wave
- `src/telemetry/serve.py` — FastAPI entry point wiring all features
- `web/` — frontend project files (package.json, config, public assets, Vite)

## Scope (out)

- WebSocket reconnection/backoff strategy beyond a simple reconnect on close.
- Authentication on WebSocket (API key via query param placeholder only).
- Kafka/Redpanda consumer-based push — broadcast from the ingest handler only.

## Acceptance criteria

| # | Criterion | Scenario(s) |
|---|-----------|-------------|
| 1 | Newly ingested telemetry event is pushed to all connected WebSocket clients | @w1 |
| 2 | Frontend opens WebSocket on dashboard load and displays live events | @w1 |
| 3 | WebSocket disconnect/reconnect does not lose previously loaded events | @w2 |

## Decisions

### D1 — Push model: broadcast from the ingestion handler

- Context & forces: The frontend needs low-latency delivery of newly ingested
  events. Options: (a) poll every N seconds (already exists, high latency,
  wasted requests), (b) server-sent events (one-way push, but needs a dedicated
  endpoint and connection management), (c) WebSocket broadcast from the ingest
  handler (bidirectional, low latency, reuses the existing FastAPI app).
- Decision & why: WebSocket broadcast from the ingestion handler. When a
  telemetry event is accepted via POST /v1/telemetry, the handler broadcasts it
  to all connected WebSocket clients. This gives sub-second delivery and no
  wasted polling.
- Consequences:
  - Positive: near real-time updates, no polling waste, single connection per
    client.
  - Negative: WebSocket state lives in the single server process; scaling to
    multiple workers requires a pub/sub layer (Redis) — out of scope for MVP.
- Reversibility: two-way door — polling remains as a fallback.

### D2 — Frontend: WebSocket primary, polling fallback

- Context & forces: The React dashboard currently polls on refresh. Adding
  WebSocket requires connection lifecycle management (open on mount, close on
  unmount, reconnect on close).
- Options considered:
  1. WebSocket only (cleaner, but no fallback for blocked clients).
  2. Polling only (existing, high latency).
  3. WebSocket primary + polling fallback (best of both).
- Decision & why: WebSocket primary + polling fallback. The dashboard opens a
  WebSocket on mount; if the connection fails or is unavailable, the existing
  refresh button still works via polling.
- Consequences:
  - Positive: real-time updates for WebSocket clients, graceful degradation.
  - Negative: more client code (connection lifecycle, message handling).
- Reversibility: two-way door — removing WebSocket leaves polling intact.

## Stack decision

- Backend: FastAPI WebSocket (`/v1/ws/telemetry`) broadcasting from the ingest
  handler. No change to the domain core.
- Frontend: React `useEffect` + `WebSocket` API on dashboard mount; existing
  polling refresh kept as fallback.
- Event bus (observed via backend): Apache Kafka / Redpanda, unchanged.
