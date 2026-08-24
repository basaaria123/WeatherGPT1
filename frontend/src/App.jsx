import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api/client'
import { useAlertsSocket } from './hooks/useAlertsSocket'
import { t } from './i18n/ui'
import { useStore } from './store/useStore'
import WeatherScene from './scene/WeatherScene'
import { sceneForCode } from './components/ui/WeatherGlyph'

import AlertsPanel from './components/AlertsPanel'
import ChatPanel from './components/ChatPanel'
import CommandCenter from './components/CommandCenter'
import DemoMode from './components/DemoMode'
import Forecast from './components/Forecast'
import Header from './components/Header'
import HistoricalNote from './components/HistoricalNote'
import ImpactGrid from './components/ImpactGrid'
import Landing from './components/Landing'
import LocationDialog from './components/LocationDialog'
import PipelinePanel from './components/PipelinePanel'
import RiskMap from './components/RiskMap'
import SplashScreen from './components/SplashScreen'
import Timeline from './components/Timeline'

/**
 * App shell.
 *
 * Owns the splash → landing → app flow and the data fetching that more than one
 * panel needs. Panel-specific loading and error state stays with the panel, so
 * one slow endpoint never blanks the rest of the dashboard.
 */

let messageId = 0
const nextId = () => { messageId += 1; return messageId }

export default function App() {
  const [stage, setStage] = useState('splash') // splash | landing | app

  const language = useStore((s) => s.language)
  const userType = useStore((s) => s.userType)
  const location = useStore((s) => s.location)
  const sessionId = useStore((s) => s.sessionId)
  const setSessionId = useStore((s) => s.setSessionId)
  const setConditions = useStore((s) => s.setConditions)
  const setCapabilities = useStore((s) => s.setCapabilities)
  const setDataSource = useStore((s) => s.setDataSource)
  const setDemoOpen = useStore((s) => s.setDemoOpen)
  const setMapFocus = useStore((s) => s.setMapFocus)
  const capabilities = useStore((s) => s.capabilities)

  const [locationOpen, setLocationOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const [currentData, setCurrentData] = useState(null)
  const [timelineData, setTimelineData] = useState(null)
  const [forecastData, setForecastData] = useState(null)
  const [mapData, setMapData] = useState(null)

  const [loading, setLoading] = useState({ current: true, timeline: true, forecast: true, map: true })
  const [errors, setErrors] = useState({})

  const [messages, setMessages] = useState([])
  const [answer, setAnswer] = useState(null)
  const [chatPending, setChatPending] = useState(false)
  const [voicePending, setVoicePending] = useState(false)
  const [chatError, setChatError] = useState(null)

  const requestSeq = useRef(0)

  useAlertsSocket()

  // --- Capabilities -------------------------------------------------------
  useEffect(() => {
    let cancelled = false
    api
      .config()
      .then((config) => {
        if (cancelled) return
        setCapabilities(config)
        setDataSource(config.data_source ?? 'live')
      })
      .catch(() => {
        /* the app still works; controls fall back to permissive defaults */
      })
    return () => { cancelled = true }
  }, [setCapabilities, setDataSource])

  // --- Weather for the selected location ----------------------------------
  const loadAll = useCallback(async () => {
    if (!location?.name) return
    const seq = ++requestSeq.current
    const params = { location: location.name, language }
    setLoading({ current: true, timeline: true, forecast: true, map: true })
    setErrors({})

    // Independent requests: one failing must not blank the others.
    const settle = (key, promise, apply) =>
      promise
        .then((data) => {
          if (seq !== requestSeq.current) return
          apply(data)
        })
        .catch((error) => {
          if (seq !== requestSeq.current) return
          setErrors((prev) => ({ ...prev, [key]: error.message }))
        })
        .finally(() => {
          if (seq !== requestSeq.current) return
          setLoading((prev) => ({ ...prev, [key]: false }))
        })

    await Promise.all([
      settle('current', api.current(params), (data) => {
        setCurrentData(data)
        setConditions({ current: data.current, risk: data.risk })
        setDataSource(data.data_source ?? 'live')
      }),
      settle('timeline', api.timeline({ location: location.name, hours: 24 }), setTimelineData),
      settle('forecast', api.forecast({ location: location.name, days: 7 }), setForecastData),
      settle('map', api.riskMap({ limit: 16 }), setMapData),
    ])
  }, [location?.name, language, setConditions, setDataSource])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const refresh = useCallback(async () => {
    setRefreshing(true)
    await loadAll()
    setRefreshing(false)
  }, [loadAll])

  // --- Chat ---------------------------------------------------------------
  const applyAnswer = useCallback(
    (data, { transcript } = {}) => {
      if (data.session_id) setSessionId(data.session_id)
      const record = { ...data, id: nextId() }
      setAnswer(record)
      setMessages((prev) => [
        ...prev,
        {
          id: record.id,
          role: 'assistant',
          text: data.answer,
          explanation: data.explanation,
          actions: data.actions ?? [],
          risk: data.risk,
          audio_base64: data.audio_base64,
          audio_mime: data.audio_mime,
          degradedNote: data.degraded?.fallback_reason || data.degraded?.tts_error || null,
        },
      ])
      // Keep the dashboard in step with what the assistant just described.
      if (data.current && data.risk) setConditions({ current: data.current, risk: data.risk })
      if (data.location?.name && data.location.name !== location?.name) {
        useStore.getState().setLocation(data.location)
      }
      if (transcript) {
        setMessages((prev) =>
          prev.map((message) =>
            message.role === 'user' && message.pendingTranscript
              ? { ...message, text: transcript, pendingTranscript: false }
              : message,
          ),
        )
      }
    },
    [setSessionId, setConditions, location?.name],
  )

  const send = useCallback(
    async (text) => {
      if (!text?.trim() || chatPending) return
      setChatError(null)
      setChatPending(true)
      setMessages((prev) => [...prev, { id: nextId(), role: 'user', text }])
      try {
        const data = await api.chat({
          query: text,
          session_id: sessionId,
          user_type: userType,
          language,
          voice_response: Boolean(capabilities?.voice_output_available),
        })
        applyAnswer(data)
      } catch (error) {
        setChatError(error.message)
      } finally {
        setChatPending(false)
      }
    },
    [chatPending, sessionId, userType, language, capabilities, applyAnswer],
  )

  const sendVoice = useCallback(
    async (blob, clientTranscript) => {
      setChatError(null)
      setVoicePending(true)
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'user', text: clientTranscript || '…', transcript: true, pendingTranscript: !clientTranscript },
      ])
      try {
        const form = new FormData()
        form.append('audio', blob, 'question.webm')
        if (sessionId) form.append('session_id', sessionId)
        if (userType) form.append('user_type', userType)
        if (language) form.append('lang', language)
        if (clientTranscript) form.append('client_transcript', clientTranscript)
        form.append('voice_response', String(Boolean(capabilities?.voice_output_available)))

        const data = await api.voiceChat(form)
        applyAnswer(data, { transcript: data.transcript })
      } catch (error) {
        setChatError(error.message)
        setMessages((prev) => prev.filter((message) => !message.pendingTranscript))
      } finally {
        setVoicePending(false)
      }
    },
    [sessionId, userType, language, capabilities, applyAnswer],
  )

  // --- Background scene ---------------------------------------------------
  const current = useStore((s) => s.current)
  const risk = useStore((s) => s.risk)
  const scene = useMemo(() => {
    if (risk?.detected_hazard === 'Extreme Heat') return 'heat'
    if (risk?.risk_level === 'Severe' || risk?.detected_hazard === 'Lightning/Storm') return 'storm'
    return sceneForCode(current?.weather_code)
  }, [current?.weather_code, risk])

  const viewArea = useCallback(
    (alert) => {
      setMapFocus({ latitude: alert.latitude, longitude: alert.longitude, at: Date.now() })
      document.getElementById('risk-map')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    },
    [setMapFocus],
  )

  const landingCondition = currentData
    ? {
        label: currentData.location?.name,
        temperature_c: currentData.current?.temperature_c,
        conditionText: currentData.current?.condition,
        weather_code: currentData.current?.weather_code,
      }
    : null

  return (
    <>
      <WeatherScene scene={scene} intensity={stage === 'app' ? 0.75 : 1} />

      <AnimatePresence mode="wait">
        {stage === 'splash' && <SplashScreen key="splash" onDone={() => setStage('landing')} />}

        {stage === 'landing' && (
          <motion.div
            key="landing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          >
            <Landing
              onEnter={() => setStage('app')}
              onDemo={() => { setStage('app'); setTimeout(() => setDemoOpen(true), 500) }}
              scene={scene}
              condition={landingCondition}
            />
          </motion.div>
        )}

        {stage === 'app' && (
          <motion.div
            key="app"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
            className="min-h-dvh"
          >
            <Header
              onOpenLocation={() => setLocationOpen(true)}
              onRefresh={refresh}
              refreshing={refreshing}
            />

            <main className="mx-auto w-full min-w-0 max-w-7xl space-y-3 px-3 pb-16 pt-3 sm:px-6 sm:pt-5">
              <CommandCenter
                data={currentData}
                loading={loading.current}
                error={errors.current}
                onRetry={refresh}
              />

              {/* Chat beside the alert feed: the conversation never takes over
                  the dashboard, and a live alert stays visible while you type. */}
              <div className="grid min-w-0 gap-3 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
                <ChatPanel
                  messages={messages}
                  onSend={send}
                  onVoice={sendVoice}
                  pending={chatPending}
                  voicePending={voicePending}
                  error={chatError}
                  audioAvailable={capabilities?.voice_output_available}
                />
                <AlertsPanel onViewArea={viewArea} />
              </div>

              <PipelinePanel answer={answer} />

              <HistoricalNote comparison={answer?.historical_comparison} />

              <Timeline data={timelineData} loading={loading.timeline} error={errors.timeline} />

              <Forecast data={forecastData} loading={loading.forecast} error={errors.forecast} />

              <ImpactGrid impacts={answer?.impacts?.length ? answer.impacts : currentData?.impacts} />

              <RiskMap data={mapData} loading={loading.map} error={errors.map} onRetry={refresh} />

              <footer className="flex flex-wrap items-center justify-between gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setDemoOpen(true)}
                  className="rounded-[var(--radius-pill)] border border-white/12 bg-white/[0.05] px-4 py-2
                             text-xs font-medium text-ink transition hover:border-white/28 hover:bg-white/[0.1]"
                >
                  ◧ {t(language, 'demoMode')}
                </button>
                <p className="text-[10px] text-faint">
                  SIH26068 · Ministry of Earth Sciences / IMD · Data: Open-Meteo
                </p>
              </footer>
            </main>
          </motion.div>
        )}
      </AnimatePresence>

      <LocationDialog open={locationOpen} onClose={() => setLocationOpen(false)} />
      <DemoMode answer={answer} />
    </>
  )
}
