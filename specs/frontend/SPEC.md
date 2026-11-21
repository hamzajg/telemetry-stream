# Spec: frontend

> Spec-driven development artifact. This file is the contract: implementation
> is done when every acceptance criterion maps to a scenario in
> `EXAMPLES.feature` and every scenario has a passing check.

## Problem

The telemetry-stream backend (ingestion, stream processing, lakehouse storage,
device management) is complete and acceptance-validated, but there is no user
interface. Fleet/operations operators cannot monitor live device telemetry or
incidents, and platform operators cannot observe accept/reject rates or consumer
lag. All telemetry is invisible without querying the bus or storage directly.

## Users

- Fleet/operations operator — monitors live device telemetry and incidents from a dashboard.
- Platform operator — observes ingestion accept/reject rates, consumer lag, and device registration status.
- Data analyst — views historical telemetry in the lakehouse (read-only query surface).

## Outcome hypothesis

- Expected user outcome: operators can see live telemetry and incidents on a dashboard without touching Kafka or the object store directly.
- Opportunity evidence: assumption — sourced from library course section titles (IoT Data Producer, Realtime Streaming Consumer); not yet validated against production telemetry volume.
- Signal: dashboard page load time, events displayed per second, operator-reported time-to-detect-incident (baseline unknown; do not invent targets).
- Follow-up owner/date: platform operator — review after wave 1 ships.

## Scope (in)

- `ui` domain: React + TypeScript + Vite frontend served as static assets.
- HTTP client consuming the existing FastAPI `/events` and `/devices` endpoints.
- Live telemetry list with per-device filtering.
- Incident/alert surface for emergency-incident telemetry events.
- Device registry view: active count and registration details.
- Observability panel: accept/reject counters, consumer lag.

## Scope (out)

- Backend changes beyond existing endpoints (the frontend consumes the current FastAPI HTTP adapter).
- Authentication/authorization for UI users (API keys via env vars/placeholders only in MVP).
- Real-time WebSocket push (polling from the bus-backed endpoints in MVP).
- Mobile native app — web dashboard only.

## Acceptance criteria

| # | Criterion | Scenario(s) |
|---|-----------|-------------|
| 1 | Dashboard loads and displays live telemetry events from the backend | @w1 |
| 2 | Operator can filter telemetry by device id | @w1 |
| 3 | Emergency-incident events surface as incidents/alerts | @w2 |
| 4 | Device registry shows active count and registration details | @w2 |
| 5 | Observability panel shows accept/reject counters and consumer lag | @w3 |

## Decisions

### D1 — Frontend stack: React + TypeScript + Vite

- Context & forces: The frontend must consume the existing FastAPI HTTP backend, render live telemetry and incidents, and be testable without a browser stack coupling business rules to UI frameworks. The workspace already uses React + TypeScript + Vite (LoomLine), so reusing that stack minimizes tooling drift and leverages existing patterns.
- Options considered:
  1. React + TypeScript + Vite (modern, typed, fast dev server, static build, matches workspace convention).
  2. Vanilla TypeScript + Vite (no component framework, more manual DOM wiring, harder to scale as the dashboard grows).
  3. Server-rendered templates coupled to FastAPI (adds backend template coupling, contradicts the stateless backend design).
- Decision & why: React + TypeScript + Vite. Typed component model, static build output served alongside or proxied to the FastAPI backend, matches the workspace's established frontend convention.
- Consequences:
  - Positive: typed props/events, fast hot-reload dev, static assets, reusable component model, workspace-consistent tooling.
  - Negative: additional build toolchain (Node/npm), CORS or proxy config needed to reach FastAPI in dev.
- Reversibility: two-way door — swapping the UI framework is a frontend rewrite, but the backend contract (JSON over HTTP) is unchanged.

### D2 — Data fetch model: polling over HTTP

- Context & forces: The backend exposes telemetry and device data via FastAPI HTTP endpoints backed by Kafka/Redpanda and the lakehouse. The frontend needs current device state and recent events. WebSocket push would require backend changes (not in scope); server-sent events add connection management complexity.
- Options considered:
  1. Polling via fetch to FastAPI endpoints (simple, reuses existing backend, no new infra, slight staleness).
  2. WebSocket (low latency, but requires backend WebSocket handler and connection lifecycle — out of scope).
  3. Server-sent events (one-way push, but requires backend SSE endpoint — out of scope).
- Decision & why: Polling via fetch. Simplest, reuses the existing FastAPI HTTP adapter with no backend changes, and staleness is acceptable for an MVP operations dashboard.
- Consequences:
  - Positive: zero backend changes, simple client code, works over standard HTTP/CORS.
  - Negative: data is stale between polls; polling interval trades freshness for load.
- Reversibility: two-way door — adding WebSocket/SSE later is a client + backend change, but polling remains functional.

## Stack decision

- Frontend: React + TypeScript + Vite. Justification: typed component model, fast hot-reload dev, static build output, matches the workspace's established frontend convention (LoomLine), and the backend contract (JSON over HTTP) is unchanged.
- Backend (consumed): existing FastAPI HTTP adapter (Python), unchanged.
- Event bus (observed via backend): Apache Kafka / Redpanda, unchanged.
