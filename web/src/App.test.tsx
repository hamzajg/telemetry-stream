/// <reference types="vitest" />
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import App from './App'

const mockFetch = vi.fn()

beforeEach(() => {
  mockFetch.mockReset()
  mockFetch.mockResolvedValue({
    ok: true,
    json: async () => ({ events: [], count: 0 }),
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
    mockFetch.mockResolvedValueOnce({
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
    })
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('device-42')).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByText('{"reading_type":"gps","value":1}')).toBeInTheDocument()
    })
  })

  it('filters events by device id', async () => {
    mockFetch
      .mockResolvedValueOnce({
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
      })
      .mockResolvedValueOnce({
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
})
