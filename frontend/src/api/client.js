/**
 * Backend client.
 *
 * Every call funnels through `request`, which turns any failure — network,
 * HTTP, or malformed body — into an `ApiError` carrying a message that is safe
 * to show a user. Components render `error.message` directly and never see a
 * stack trace or a raw status code.
 */

const BASE = import.meta.env.VITE_API_BASE ?? '/api'

export class ApiError extends Error {
  constructor(message, { status = 0, cause } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.cause = cause
  }
}

const FRIENDLY = {
  404: 'We could not find that place. Check the spelling and try again.',
  422: 'That request was not valid. Please adjust it and try again.',
  429: 'Too many requests just now. Please wait a moment.',
  500: 'Something went wrong on our side. Please try again.',
  503: 'The weather service is unavailable right now. Please try again shortly.',
}

async function request(path, { method = 'GET', body, signal, timeout = 30000, form } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)
  // Honour a caller's own cancellation as well as our timeout.
  if (signal) signal.addEventListener('abort', () => controller.abort(), { once: true })

  try {
    const response = await fetch(`${BASE}${path}`, {
      method,
      signal: controller.signal,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: form ?? (body ? JSON.stringify(body) : undefined),
    })

    let payload = null
    const text = await response.text()
    if (text) {
      try {
        payload = JSON.parse(text)
      } catch {
        payload = null
      }
    }

    if (!response.ok) {
      const detail =
        (payload && typeof payload.detail === 'string' && payload.detail) ||
        FRIENDLY[response.status] ||
        'That did not work. Please try again.'
      throw new ApiError(detail, { status: response.status })
    }
    return payload
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error?.name === 'AbortError') {
      throw new ApiError('That took too long. Please try again.', { status: 0, cause: error })
    }
    throw new ApiError('Could not reach WeatherGPT. Check your connection and try again.', {
      status: 0,
      cause: error,
    })
  } finally {
    clearTimeout(timer)
  }
}

const qs = (params) => {
  const search = new URLSearchParams()
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  })
  const query = search.toString()
  return query ? `?${query}` : ''
}

export const api = {
  health: () => request('/health', { timeout: 8000 }),
  config: () => request('/config', { timeout: 8000 }),

  chat: (payload, options) => request('/chat', { method: 'POST', body: payload, timeout: 45000, ...options }),

  voiceChat: (formData, options) =>
    request('/voice-chat', { method: 'POST', form: formData, timeout: 60000, ...options }),

  geocode: (q) => request(`/geocode${qs({ q })}`),
  reverseGeocode: (lat, lon) => request(`/geocode/reverse${qs({ lat, lon })}`),
  current: (params) => request(`/weather/current${qs(params)}`),
  timeline: (params) => request(`/weather/timeline${qs(params)}`),
  forecast: (params) => request(`/weather/forecast${qs(params)}`),
  climateTrend: (params) => request(`/climate-trend${qs(params)}`, { timeout: 45000 }),

  alerts: (params) => request(`/alerts${qs(params)}`),
  subscribe: (payload) => request('/alerts/subscribe', { method: 'POST', body: payload }),
  scanAlerts: () => request('/alerts/scan', { method: 'POST', timeout: 60000 }),

  risk: (params) => request(`/risk${qs(params)}`),
  riskMap: (params) => request(`/risk-map${qs(params)}`, { timeout: 45000 }),

  historicalEvents: () => request('/historical-events'),
}

/** WebSocket URL for /ws/alerts, derived from the same base as HTTP calls. */
export function alertsSocketUrl() {
  if (BASE.startsWith('http')) {
    return `${BASE.replace(/^http/, 'ws')}/ws/alerts`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${BASE}/ws/alerts`
}
