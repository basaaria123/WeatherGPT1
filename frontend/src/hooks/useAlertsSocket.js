import { useEffect, useRef } from 'react'
import { alertsSocketUrl, api } from '../api/client'
import { useStore } from '../store/useStore'

/**
 * Live alert feed.
 *
 * Prefers a WebSocket to /ws/alerts. Two things make that unreliable in the
 * wild, and both are handled rather than left to fail:
 *
 * 1. Serverless hosts cannot hold a socket open across invocations. The backend
 *    says so in /config (`websockets_supported: false`), so the client goes
 *    straight to polling instead of failing three times first.
 * 2. Proxies and captive networks drop long-lived sockets. After a few failed
 *    attempts the client falls back to polling on its own.
 *
 * Either way the alert list stays current; only the latency changes. Because
 * the server replays a snapshot on connect, a drop during an alert storm
 * self-heals rather than leaving a hole.
 */

const MAX_BACKOFF = 15000
const FAILURES_BEFORE_POLLING = 3
const DEFAULT_POLL_MS = 60000

export function useAlertsSocket() {
  const setAlerts = useStore((s) => s.setAlerts)
  const pushAlert = useStore((s) => s.pushAlert)
  const setSocketState = useStore((s) => s.setSocketState)

  // Capabilities are read non-reactively, at the moment a decision is made.
  // Subscribing to them would tear the socket down and rebuild it the instant
  // /config resolves, which is churn for no gain: if a socket is already open
  // it works, and if it is not the failure path handles it.
  const failureThreshold = () =>
    useStore.getState().capabilities?.websockets_supported === false
      ? 1 // the backend says sockets cannot work here — do not labour the point
      : FAILURES_BEFORE_POLLING

  const pollInterval = () =>
    (useStore.getState().capabilities?.alert_poll_seconds ?? DEFAULT_POLL_MS / 1000) * 1000

  const socketRef = useRef(null)
  const retryRef = useRef(0)
  const timerRef = useRef(null)
  const heartbeatRef = useRef(null)
  const pollRef = useRef(null)
  const stopped = useRef(false)

  useEffect(() => {
    stopped.current = false

    const clearTimers = () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      if (heartbeatRef.current) clearInterval(heartbeatRef.current)
      timerRef.current = null
      heartbeatRef.current = null
    }

    const stopPolling = () => {
      if (pollRef.current) clearInterval(pollRef.current)
      pollRef.current = null
    }

    const fetchOnce = async () => {
      try {
        const data = await api.alerts({ limit: 40 })
        if (!stopped.current && Array.isArray(data?.alerts)) setAlerts(data.alerts)
      } catch {
        /* a failed poll is not fatal; the next tick tries again */
      }
    }

    const startPolling = () => {
      if (pollRef.current || stopped.current) return
      setSocketState('polling')
      fetchOnce()
      pollRef.current = setInterval(fetchOnce, pollInterval())
    }

    const scheduleRetry = () => {
      if (stopped.current) return
      retryRef.current += 1
      if (retryRef.current >= failureThreshold()) {
        startPolling()
        return
      }
      timerRef.current = setTimeout(connect, Math.min(MAX_BACKOFF, 1000 * 2 ** retryRef.current))
    }

    function connect() {
      if (stopped.current) return
      setSocketState(retryRef.current === 0 ? 'connecting' : 'reconnecting')

      let socket
      try {
        socket = new WebSocket(alertsSocketUrl())
      } catch {
        scheduleRetry()
        return
      }
      socketRef.current = socket

      socket.onopen = () => {
        retryRef.current = 0
        stopPolling()
        setSocketState('open')
        heartbeatRef.current = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) socket.send('ping')
        }, 20000)
      }

      socket.onmessage = (event) => {
        let message
        try {
          message = JSON.parse(event.data)
        } catch {
          return
        }
        if (message.type === 'snapshot' && Array.isArray(message.alerts)) setAlerts(message.alerts)
        else if (message.type === 'alert' && message.alert) pushAlert(message.alert)
      }

      socket.onclose = () => {
        clearTimers()
        if (stopped.current) return
        setSocketState('closed')
        scheduleRetry()
      }
    }

    // Always try the socket first, even before /config has resolved: it is the
    // better transport when it works, and the failure path is cheap.
    connect()

    return () => {
      stopped.current = true
      clearTimers()
      stopPolling()
      const socket = socketRef.current
      if (!socket) return
      if (socket.readyState === WebSocket.OPEN) {
        socket.close()
      } else if (socket.readyState === WebSocket.CONNECTING) {
        // Closing a connecting socket logs a warning, which StrictMode's
        // double-mount would produce on every dev start. Wait, then close.
        socket.addEventListener('open', () => socket.close(), { once: true })
      }
    }
    // Deliberately stable: this effect owns one connection for the component's
    // lifetime and must not be restarted by unrelated state changes.
  }, [setAlerts, pushAlert, setSocketState])
}
