import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api/client'
import { useAlertsSocket } from './hooks/useAlertsSocket'
import { t } from './i18n/ui'
import { useStore } from './store/useStore'
import WeatherScene from './scene/WeatherScene'
import { THEMES, applyTheme, resolveTheme, sceneForCondition } from './theme/weatherTheme'

import AdvisoryCard from './components/AdvisoryCard'
import AlertsPanel from './components/AlertsPanel'
import EmergencyBanner from './components/EmergencyBanner'
import HistoricalContext from './components/HistoricalContext'
import PersonaCompare from './components/PersonaCompare'
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
  const [compareOpen, setCompareOpen] = useState(false)
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
  // `location` in the store is the single source of truth. Every panel below
  // renders from data fetched for it, and `requestSeq` drops any response that
  // arrives after the selection has moved on — so a slow request for the
  // previous city can never repaint the new one's dashboard.
  const loadAll = useCallback(async () => {
    if (!location?.name) return
    const seq = ++requestSeq.current
    const params = { location: location.name, language, user_type: userType }
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
  }, [location?.name, language, userType, setConditions, setDataSource])

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
      // Stamp the answer with the place it actually describes. Panels below
      // compare this against the selected location and drop the answer when it
      // no longer matches, which is what stops a Guwahati reading surviving a
      // switch to Mumbai.
      const describes = data.location?.name ?? location?.name ?? ''
      const record = { ...data, id: nextId(), describesLocation: describes }
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
          // The language the answer was written in, so speech uses the right
          // voice rather than reading Telugu with an English one.
          lang: data.language ?? language,
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
          // The dashboard's selection travels with the question, so an answer
          // can never describe a different place from the one on screen.
          location: location?.name,
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
    [chatPending, sessionId, userType, language, capabilities, applyAnswer, location?.name],
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
        if (location?.name) form.append('location', location.name)
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
    [sessionId, userType, language, capabilities, applyAnswer, location?.name],
  )

  // --- One resolved weather state drives scene, theme and every label ------
  // Read from `currentData` rather than the store mirror so the atmosphere can
  // never lag a location change by a render.
  const shown = currentData?.current
  const shownRisk = currentData?.risk

  const scene = useMemo(
    () =>
      sceneForCondition({
        weatherCode: shown?.weather_code,
        riskLevel: shownRisk?.risk_level,
        hazard: shownRisk?.detected_hazard,
      }),
    [shown?.weather_code, shownRisk?.risk_level, shownRisk?.detected_hazard],
  )

  const themeKey = useMemo(
    () =>
      resolveTheme({
        weatherCode: shown?.weather_code,
        isDay: shown?.is_day,
        riskLevel: shownRisk?.risk_level,
        hazard: shownRisk?.detected_hazard,
      }),
    [shown?.weather_code, shown?.is_day, shownRisk?.risk_level, shownRisk?.detected_hazard],
  )

  useEffect(() => {
    applyTheme(themeKey)
  }, [themeKey])

  const lightTheme = THEMES[themeKey]?.scheme === 'light'

  // An answer only counts for the place currently selected.
  const answerHere =
    answer && answer.describesLocation === (location?.name ?? '') ? answer : null

  // All three depth features read the same risk output. The dashboard's own
  // reading leads; a chat answer for this location can supply it before the
  // dashboard has finished loading.
  const advisory = currentData?.advisory ?? answerHere?.advisory ?? null
  const emergency = currentData?.emergency ?? answerHere?.emergency ?? null
  const similarity = answerHere?.historical_similarity ?? null

  const viewArea = useCallback(
    (alert) => {
      setMapFocus({ latitude: alert.latitude, longitude: alert.longitude, at: Date.now() })
      document.getElementById('risk-map')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    },
    [setMapFocus],
  )

  return (
    <>
      <WeatherScene scene={scene} light={lightTheme} intensity={stage === 'app' ? 0.75 : 1} />

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
            {/* The landing page introduces the product; it deliberately shows no
                live condition, temperature or location. */}
            <Landing
              onEnter={() => setStage('app')}
              onDemo={() => { setStage('app'); setTimeout(() => setDemoOpen(true), 500) }}
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
            {/* Straight back to the landing page — never via the splash, which
                belongs to first load only. */}
            <Header
              onHome={() => setStage('landing')}
              onOpenLocation={() => setLocationOpen(true)}
              onRefresh={refresh}
              refreshing={refreshing}
            />

            <main className="mx-auto w-full min-w-0 max-w-7xl space-y-3 px-3 pb-16 pt-3 sm:px-6 sm:pt-5">
              {/* Level 0 when it fires: what is happening now, above all else. */}
              <EmergencyBanner
                emergency={emergency}
                audioBase64={answerHere?.audio_base64}
                audioMime={answerHere?.audio_mime}
              />

              {/* Under an active emergency the actions come before the reading;
                  nothing is hidden, it is reprioritised. */}
              {emergency?.active && (
                <AdvisoryCard advisory={advisory} onCompare={() => setCompareOpen(true)} />
              )}

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
                  insight={currentData?.insight}
                  insightLoading={loading.current}
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

              {!emergency?.active && (
                <AdvisoryCard advisory={advisory} onCompare={() => setCompareOpen(true)} />
              )}

              <PipelinePanel answer={answerHere} />

              <HistoricalContext similarity={similarity} />

              <HistoricalNote comparison={similarity?.matched ? null : answerHere?.historical_comparison} />

              <Timeline data={timelineData} loading={loading.timeline} error={errors.timeline} />

              <Forecast data={forecastData} loading={loading.forecast} error={errors.forecast} />

              <ImpactGrid
                impacts={answerHere?.impacts?.length ? answerHere.impacts : currentData?.impacts}
                loading={loading.current}
              />

              <RiskMap
                data={mapData}
                loading={loading.map}
                error={errors.map}
                onRetry={refresh}
                onSelect={(entry) =>
                  useStore.getState().setLocation({
                    name: entry.location,
                    admin1: entry.admin1,
                    latitude: entry.latitude,
                    longitude: entry.longitude,
                  })
                }
              />

              <footer className="flex flex-wrap items-center justify-between gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setDemoOpen(true)}
                  className="rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.12)] bg-[rgb(var(--wx-tint)/0.05)] px-4 py-2
                             text-xs font-medium text-ink transition hover:border-[rgb(var(--wx-tint)/0.28)] hover:bg-[rgb(var(--wx-tint)/0.1)]"
                >
                  ◧ {t(language, 'demoMode')}
                </button>
                <DataProvenance generatedAt={currentData?.generated_at} />
              </footer>
            </main>
          </motion.div>
        )}
      </AnimatePresence>

      <PersonaCompare
        open={compareOpen}
        onClose={() => setCompareOpen(false)}
        location={location?.name}
      />
      <LocationDialog open={locationOpen} onClose={() => setLocationOpen(false)} />
      <DemoMode answer={answerHere} />
    </>
  )
}

/**
 * Data provenance.
 *
 * Names the provider actually in use and when this reading was taken. In
 * fixture mode it says so plainly rather than dressing simulated numbers up as
 * a live feed.
 */
function DataProvenance({ generatedAt }) {
  const language = useStore((s) => s.language)
  const dataSource = useStore((s) => s.dataSource)
  const simulated = dataSource === 'fixture'

  const stamp = (() => {
    if (!generatedAt) return null
    const at = new Date(generatedAt)
    if (Number.isNaN(at.getTime())) return null
    return at.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  })()

  return (
    <p className="text-[11px] leading-relaxed text-faint">
      <span className={simulated ? 'text-caution' : ''}>
        {simulated ? t(language, 'sourceSimulated') : t(language, 'sourceLive')}
      </span>
      {stamp && <> · {t(language, 'updated')} {stamp}</>}
    </p>
  )
}
