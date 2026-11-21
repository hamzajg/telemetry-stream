import { useState, useEffect, useCallback } from 'react'

interface TelemetryEvent {
  device_id: string
  sequence: number
  payload: Record<string, unknown>
  timestamp: string
  offset: number
}

interface TelemetryResponse {
  events: TelemetryEvent[]
  count: number
}

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

function fetchEvents(deviceId?: string): Promise<TelemetryResponse> {
  const url = deviceId
    ? `${API_BASE}/v1/telemetry?device_id=${encodeURIComponent(deviceId)}`
    : `${API_BASE}/v1/telemetry`
  return fetch(url).then(async (res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.json() as Promise<TelemetryResponse>
  })
}

function TelemetryDashboard() {
  const [events, setEvents] = useState<TelemetryEvent[]>([])
  const [deviceFilter, setDeviceFilter] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    fetchEvents(deviceFilter || undefined)
      .then((data) => setEvents(data.events))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [deviceFilter])

  useEffect(() => {
    load()
  }, [load])

  const filtered = deviceFilter
    ? events.filter((e) => e.device_id === deviceFilter)
    : events

  return (
    <div className="dashboard">
      <header>
        <h1>Telemetry Stream</h1>
        <p>Live IoT device telemetry ingestion dashboard</p>
      </header>

      <div className="toolbar">
        <input
          type="text"
          placeholder="Filter by device id"
          value={deviceFilter}
          onChange={(e) => setDeviceFilter(e.target.value)}
        />
        <button onClick={load} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && <div className="error">Error: {error}</div>}

      <div className="summary">
        <span>{events.length} event(s)</span>
        {deviceFilter && <span>filtered by "{deviceFilter}"</span>}
      </div>

      <table>
        <thead>
          <tr>
            <th>Offset</th>
            <th>Device</th>
            <th>Sequence</th>
            <th>Timestamp</th>
            <th>Payload</th>
          </tr>
        </thead>
        <tbody>
          {filtered.length === 0 && (
            <tr>
              <td colSpan={5}>No telemetry events</td>
            </tr>
          )}
          {filtered.map((event) => (
            <tr key={`${event.device_id}-${event.sequence}`}>
              <td>{event.offset}</td>
              <td>{event.device_id}</td>
              <td>{event.sequence}</td>
              <td>{event.timestamp}</td>
              <td>{JSON.stringify(event.payload)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default TelemetryDashboard
