/// <reference types="vitest" />
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import App from './App'

const mockFetch = vi.fn()

// Mock WebSocket for live-updates tests
class MockWebSocket {
  static instances: MockWebSocket[] = []
  onopen: ((e: Event) => void) | null = null
  onclose: ((e: Event) => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  readyState = 1
  send = vi.fn()
  close = vi.fn()

  constructor(_url: string) {
    MockWebSocket.instances.push(this)
    setTimeout(() => {
      this.onopen?.(new Event('open'))
    }, 0)
  }

  static triggerMessage(data: string) {
    MockWebSocket.instances.forEach((ws) => {
      ws.onmessage?.(new MessageEvent('message', { data }))
    })
  }

  static triggerClose() {
    MockWebSocket.instances.forEach((ws) => {
      ws.onclose?.(new Event('close'))
    })
  }

  static clear() {
    MockWebSocket.instances = []
  }
}

;(globalThis as any).WebSocket = MockWebSocket

beforeEach(() => {
  mockFetch.mockReset()
  MockWebSocket.clear()
  mockFetch.mockImplementation(async (url: string) => {
    if (String(url).includes('/v1/devices')) {
      return {
        ok: true,
        json: async () => ({
          active_count: 2,
          devices: [
            {
              device_id: 'device-42',
              registered_at: '2026-01-01T00:00:00Z',
              active: true,
            },
            {
              device_id: 'device-99',
              registered_at: '2026-01-01T00:00:01Z',
              active: false,
            },
          ],
        }),
      }
    }
    if (String(url).includes('/v1/metrics')) {
      return {
        ok: true,
        json: async () => ({
          accept_count: 10,
          reject_count: 2,
          consumer_lag_by_device: { 'device-42': 3, 'device-99': 0 },
        }),
      }
    }
    return {
      ok: true,
      json: async () => ({ events: [], count: 0 }),
    }
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

vi.stubGlobal('fetch', mockFetch)

describe('TelemetryDashboard', () => {
  it('renders the dashboard header', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /telemetry stream/i })).toBeInTheDocument()
  })

  it('shows no events message when empty', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('No telemetry events')).toBeInTheDocument()
    })
  })

  it('displays telemetry events', async () => {
    mockFetch.mockImplementationOnce(async (url: string) => {
      if (String(url).includes('/v1/devices')) {
        return {
          ok: true,
          json: async () => ({ active_count: 0, devices: [] }),
        }
      }
      return {
        ok: true,
        json: async () => ({
          events: [
            {
              device_id: 'device-42',
              sequence: 1,
              payload: { reading_type: 'gps', value: 1.0 },
              timestamp: '2026-01-01T00:00:00Z',
              offset: 1,
            },
          ],
          count: 1,
        }),
      }
    })
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('device-42')).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByText('{"reading_type":"gps","value":1}')).toBeInTheDocument()
    })
  })

  it('emergency-incident events surface as incidents are highlighted', async () => {
    mockFetch.mockImplementationOnce(async (url: string) => {
      if (String(url).includes('/v1/devices')) {
        return {
          ok: true,
          json: async () => ({ active_count: 0, devices: [] }),
        }
      }
      return {
        ok: true,
        json: async () => ({
          events: [
            {
              device_id: 'device-42',
              sequence: 1,
              payload: { reading_type: 'emergency_incident', severity: 'high' },
              timestamp: '2026-01-01T00:00:00Z',
              offset: 1,
            },
          ],
          count: 1,
        }),
      }
    })
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('device-42')).toBeInTheDocument()
    })
    const row = screen.getByText('device-42').closest('tr')
    expect(row).toHaveClass('incident')
  })

  it('filters events by device id', async () => {
    mockFetch.mockImplementationOnce(async (url: string) => {
      if (String(url).includes('/v1/devices')) {
        return {
          ok: true,
          json: async () => ({ active_count: 0, devices: [] }),
        }
      }
      return {
        ok: true,
        json: async () => ({
          events: [
            {
              device_id: 'device-42',
              sequence: 1,
              payload: { reading_type: 'gps' },
              timestamp: '2026-01-01T00:00:00Z',
              offset: 1,
            },
            {
              device_id: 'device-99',
              sequence: 1,
              payload: { reading_type: 'weather' },
              timestamp: '2026-01-01T00:00:01Z',
              offset: 1,
            },
          ],
          count: 2,
        }),
      }
    })
    .mockImplementationOnce(async (url: string) => {
      if (String(url).includes('/v1/devices')) {
        return {
          ok: true,
          json: async () => ({ active_count: 0, devices: [] }),
        }
      }
      return {
        ok: true,
        json: async () => ({
          events: [
            {
              device_id: 'device-42',
              sequence: 1,
              payload: { reading_type: 'gps' },
              timestamp: '2026-01-01T00:00:00Z',
              offset: 1,
            },
          ],
          count: 1,
        }),
      }
    })

    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('device-42')).toBeInTheDocument()
      expect(screen.getByText('device-99')).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/filter by device id/i)
    fireEvent.change(input, { target: { value: 'device-42' } })
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /refresh/i })).not.toBeDisabled()
    })
    fireEvent.click(screen.getByRole('button', { name: /refresh/i }))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenLastCalledWith(
        expect.stringContaining('device_id=device-42')
      )
    })
  })

  it('shows error when fetch fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('network error'))
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText(/error: network error/i)).toBeInTheDocument()
    })
  })

  it('shows WebSocket offline status when no API base configured', () => {
    render(<App />)
    expect(screen.getByText('○ Offline')).toBeInTheDocument()
  })

  it('seed button calls /v1/seed and reloads events', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ events: [], count: 0 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ accepted: 4, rejected: 0, total: 4 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ events: [], count: 0 }),
      })

    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('○ Offline')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /seed demo data/i }))
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/v1/seed'),
        expect.objectContaining({ method: 'POST' })
      )
    })
  })

  it('WebSocket connects and shows live status', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ events: [], count: 0 }),
    })
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('● Live')).toBeInTheDocument()
    })
  })

  it('WebSocket disconnect keeps events and reconnects', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        events: [
          {
            device_id: 'device-42',
            sequence: 1,
            payload: { reading_type: 'temperature', value: 22.5 },
            timestamp: '2026-01-01T00:00:00Z',
            offset: 1,
          },
        ],
        count: 1,
      }),
    })
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('device-42')).toBeInTheDocument()
      expect(screen.getByText('● Live')).toBeInTheDocument()
    })

    // Simulate disconnect
    await act(async () => {
      MockWebSocket.triggerClose()
    })
    await waitFor(() => {
      expect(screen.getByText('⟳ Reconnecting…')).toBeInTheDocument()
    })
    // Events remain visible
    expect(screen.getByText('device-42')).toBeInTheDocument()

    // Simulate reconnect
    MockWebSocket.instances[0].onopen?.(new Event('open'))
    await waitFor(() => {
      expect(screen.getByText('● Live')).toBeInTheDocument()
    })
  })

  it('WebSocket pushes live events to the dashboard', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ events: [], count: 0 }),
    })
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('● Live')).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.queryByText('No telemetry events')).toBeInTheDocument()
    })

    // Simulate server pushing a new event via WebSocket
    MockWebSocket.triggerMessage(
      JSON.stringify({
        type: 'telemetry',
        device_id: 'device-77',
        sequence: 1,
        payload: { reading_type: 'gps', value: 1.0 },
        timestamp: '2026-01-01T00:00:00Z',
        offset: 1,
      })
    )
    await waitFor(() => {
      expect(screen.getByText('device-77')).toBeInTheDocument()
    })
  })
})

describe('DeviceRegistry', () => {
  it('renders device registry header and device list', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /devices/i }))
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /device registry/i })).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByText('device-42')).toBeInTheDocument()
      expect(screen.getByText('device-99')).toBeInTheDocument()
    })
  })

  it('shows active device count', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /devices/i }))
    await waitFor(() => {
      expect(screen.getByText('2 active device(s)')).toBeInTheDocument()
    })
  })

  it('shows inactive devices with inactive styling', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /devices/i }))
    await waitFor(() => {
      expect(screen.getByText('device-99')).toBeInTheDocument()
    })
    const row = screen.getByText('device-99').closest('tr')
    expect(row).toHaveClass('inactive')
  })
})

describe('ObservabilityPanel', () => {
  it('observability panel shows accept/reject counters and consumer lag', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /observability/i }))
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /observability/i })).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByText('Accepted: 10')).toBeInTheDocument()
      expect(screen.getByText('Rejected: 2')).toBeInTheDocument()
    })
  })

  it('shows consumer lag by device', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /observability/i }))
    await waitFor(() => {
      expect(screen.getByText('device-42')).toBeInTheDocument()
      expect(screen.getByText('3')).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByText('device-99')).toBeInTheDocument()
    })
  })

  it('shows zero lag without lagging class', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /observability/i }))
    await waitFor(() => {
      expect(screen.getByText('device-99')).toBeInTheDocument()
    })
    const row = screen.getByText('device-99').closest('tr')
    expect(row).not.toHaveClass('lagging')
  })

  it('shows lagging class for positive lag', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /observability/i }))
    await waitFor(() => {
      expect(screen.getByText('device-42')).toBeInTheDocument()
    })
    const row = screen.getByText('device-42').closest('tr')
    expect(row).toHaveClass('lagging')
  })
})
