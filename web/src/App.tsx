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

interface Device {
  device_id: string
  registered_at: string
  active: boolean
}

interface DevicesResponse {
  active_count: number
  devices: Device[]
}

interface MetricsResponse {
  accept_count: number
  reject_count: number
  consumer_lag_by_device: Record<string, number>
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

function fetchDevices(): Promise<DevicesResponse> {
  return fetch(`${API_BASE}/v1/devices`).then(async (res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.json() as Promise<DevicesResponse>
  })
}

function fetchMetrics(): Promise<MetricsResponse> {
  return fetch(`${API_BASE}/v1/metrics`).then(async (res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.json() as Promise<MetricsResponse>
  })
}

function isEmergencyIncident(event: TelemetryEvent): boolean {
  return (
    (event.payload as Record<string, unknown>)?.reading_type === 'emergency_incident'
  )
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
            <tr
              key={`${event.device_id}-${event.sequence}`}
              className={isEmergencyIncident(event) ? 'incident' : ''}
            >
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

function DeviceRegistry() {
  const [devices, setDevices] = useState<Device[]>([])
  const [activeCount, setActiveCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    fetchDevices()
      .then((data) => {
        setDevices(data.devices)
        setActiveCount(data.active_count)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="dashboard">
      <header>
        <h1>Device Registry</h1>
        <p>Registered devices and their status</p>
      </header>

      <div className="toolbar">
        <button onClick={load} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && <div className="error">Error: {error}</div>}

      <div className="summary">
        <span>{activeCount} active device(s)</span>
        <span>{devices.length} total</span>
      </div>

      <table>
        <thead>
          <tr>
            <th>Device</th>
            <th>Registered At</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {devices.length === 0 && (
            <tr>
              <td colSpan={3}>No registered devices</td>
            </tr>
          )}
          {devices.map((device) => (
            <tr key={device.device_id} className={!device.active ? 'inactive' : ''}>
              <td>{device.device_id}</td>
              <td>{device.registered_at}</td>
              <td>
                {device.active ? 'Active' : 'Inactive'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ObservabilityPanel() {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    fetchMetrics()
      .then((data) => setMetrics(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const lagEntries = metrics ? Object.entries(metrics.consumer_lag_by_device) : []

  return (
    <div className="dashboard">
      <header>
        <h1>Observability</h1>
        <p>Ingestion health: accept/reject counters and consumer lag</p>
      </header>

      <div className="toolbar">
        <button onClick={load} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && <div className="error">Error: {error}</div>}

      {metrics === null && (
        <div className="summary">
          <span>Loading metrics…</span>
        </div>
      )}

      {metrics !== null && (
        <>
          <div className="summary">
            <span className="metric">Accepted: {metrics.accept_count}</span>
            <span className="metric">Rejected: {metrics.reject_count}</span>
            <span className="metric">Total: {metrics.accept_count + metrics.reject_count}</span>
          </div>

          <table>
            <thead>
              <tr>
                <th>Device</th>
                <th>Consumer Lag</th>
              </tr>
            </thead>
            <tbody>
              {lagEntries.length === 0 && (
                <tr>
                  <td colSpan={2}>No consumer lag data</td>
                </tr>
              )}
              {lagEntries.map(([deviceId, lag]) => (
                <tr key={deviceId} className={lag > 0 ? 'lagging' : ''}>
                  <td>{deviceId}</td>
                  <td>{lag}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}

export default function App() {
  const [view, setView] = useState<'telemetry' | 'devices' | 'observability'>('telemetry')

  return (
    <div className="app">
      <nav>
        <button
          onClick={() => setView('telemetry')}
          className={view === 'telemetry' ? 'active' : ''}
        >
          Telemetry
        </button>
        <button
          onClick={() => setView('devices')}
          className={view === 'devices' ? 'active' : ''}
        >
          Devices
        </button>
        <button
          onClick={() => setView('observability')}
          className={view === 'observability' ? 'active' : ''}
        >
          Observability
        </button>
      </nav>
      {view === 'telemetry' ? <TelemetryDashboard /> : view === 'devices' ? <DeviceRegistry /> : <ObservabilityPanel />}
    </div>
  )
}
