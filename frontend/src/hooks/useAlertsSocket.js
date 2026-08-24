import { useEffect, useRef } from 'react'
import { alertsSocketUrl } from '../api/client'
import { useStore } from '../store/useStore'

/**
 * Live alert feed over /ws/alerts.
 *
 * Reconnects with capped exponential backoff, and because the server replays a
 * snapshot on every connect, a drop during an alert storm self-heals: the
 * client's list is rebuilt from the snapshot rather than left with a hole.
 */
const MAX_BACKOFF = 15000

export function useAlertsSocket() {
  const setAlerts = useStore((s) => s.setAlerts)
  const pushAlert = useStore((s) => s.pushAlert)
  const setSocketState = useStore((s) => s.setSocketState)

  const socketRef = useRef(null)
  const retryRef = useRef(0)
  const timerRef = useRef(null)
  const heartbeatRef = useRef(null)
  const closedByUs = useRef(false)

  useEffect(() => {
    closedByUs.current = false

    const clearTimers = () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      if (heartbeatRef.current) clearInterval(heartbeatRef.current)
      timerRef.current = null
      heartbeatRef.current = null
    }

    const connect = () => {
      if (closedByUs.current) return
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
        setSocketState('open')
        // Keep intermediaries from closing an idle socket.
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
        if (message.type === 'snapshot' && Array.isArray(message.alerts)) {
          setAlerts(message.alerts)
        } else if (message.type === 'alert' && message.alert) {
          pushAlert(message.alert)
        }
      }

      socket.onerror = () => {
        // onclose always follows; retry logic lives there.
      }

      socket.onclose = () => {
        clearTimers()
        if (closedByUs.current) return
        setSocketState('closed')
        scheduleRetry()
      }
    }

    const scheduleRetry = () => {
      const delay = Math.min(MAX_BACKOFF, 1000 * 2 ** retryRef.current)
      retryRef.current += 1
      timerRef.current = setTimeout(connect, delay)
    }

    connect()

    return () => {
      closedByUs.current = true
      clearTimers()
      const socket = socketRef.current
      if (!socket) return
      if (socket.readyState === WebSocket.OPEN) {
        socket.close()
      } else if (socket.readyState === WebSocket.CONNECTING) {
        // Closing a still-connecting socket logs a console warning, which
        // StrictMode's double-mount would produce on every dev start. Wait for
        // the handshake, then close cleanly.
        socket.addEventListener('open', () => socket.close(), { once: true })
      }
    }
  }, [setAlerts, pushAlert, setSocketState])
}
