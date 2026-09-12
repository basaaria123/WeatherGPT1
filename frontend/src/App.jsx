import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api/client'
import { userMessage } from './api/errors'
import { useAlertsSocket } from './hooks/useAlertsSocket'
import { t } from './i18n/ui'
import { useStore } from './store/useStore'
import WeatherScene from './scene/WeatherScene'
import { isNightFor } from './theme/daynight'
import { THEMES, applyTheme, approachingScene, resolveTheme, sceneForCondition } from './theme/weatherTheme'

import AdvisoryCard from './components/AdvisoryCard'
import AlertIndicator from './components/AlertIndicator'
import AlertsCenter from './components/AlertsCenter'
import BottomNav from './components/BottomNav'
import EmergencyBanner from './components/EmergencyBanner'
import HistoricalContext from './components/HistoricalContext'
import PersonaCompare from './components/PersonaCompare'
import ChatPanel from './components/ChatPanel'
import CommandCenter from './components/CommandCenter'
import DemoMode from './components/DemoMode'
import Forecast from './components/Forecast'
import Header from './components/Header'
import HistoricalNote from './components/HistoricalNote'
import Landing from './components/Landing'
import Onboarding from './components/onboarding/Onboarding'
import LocationDialog from './components/LocationDialog'
import PipelinePanel from './components/PipelinePanel'
import RiskMap from './components/RiskMap'
import RoleIntelligence from './components/RoleIntelligence'
import MapLauncher from './components/MapLauncher'
import WeatherMap from './components/WeatherMap'
import SplashScreen from './components/SplashScreen'
import Timeline from './components/Timeline'
import WeatherIntro from './components/WeatherIntro'

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
  // splash → landing → onboarding (first visit only) → app. A returning
  // reader has `onboarded` remembered and never sees the questions again.
  const [stage, setStage] = useState('splash')
  // Which of the five destinations is showing. Nested inside `stage` rather
  // than replacing it: splash, landing and onboarding are not destinations,
  // they are the road to them.
  const [screen, setScreen] = useState('home')

  const language = useStore((s) => s.language)
  const appearance = useStore((s) => s.appearance)
  const userType = useStore((s) => s.userType)
  const location = useStore((s) => s.location)
  const setLocation = useStore((s) => s.setLocation)
  const sessionId = useStore((s) => s.sessionId)
  const setSessionId = useStore((s) => s.setSessionId)
  const setConditions = useStore((s) => s.setConditions)
  const setCapabilities = useStore((s) => s.setCapabilities)
  const setDataSource = useStore((s) => s.setDataSource)
  const setDemoOpen = useStore((s) => s.setDemoOpen)
  const setMapFocus = useStore((s) => s.setMapFocus)
  const capabilities = useStore((s) => s.capabilities)
  const onboarded = useStore((s) => s.onboarded)

  const [locationOpen, setLocationOpen] = useState(false)
  // Which panel onboarding opens on: the first question on a first visit, the
  // identity panel when the reader asked to sign in.
  const [onboardAt, setOnboardAt] = useState('location')
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
          setErrors((prev) => ({ ...prev, [key]: userMessage(error, language) }))
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
      // `user_type` and `language` add the per-hour readings the map explains
      // itself with; `hours` carries each mapped location's own forecast so the
      // playback steps real values instead of animating one.
      settle(
        'timeline',
        api.timeline({ location: location.name, hours: 24, user_type: userType, language }),
        setTimelineData,
      ),
      settle('forecast', api.forecast({ location: location.name, days: 7, language }), setForecastData),
      // `user_type` and `language` are what let each mapped location carry its
      // own one-line reading, written for whoever is looking at the map.
      settle(
        'map',
        api.riskMap({ limit: 16, hours: 6, user_type: userType, language }),
        setMapData,
      ),
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
        setChatError(userMessage(error, language))
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
        setChatError(userMessage(error, language))
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

  /**
   * Night at the *selected location*, re-asked every minute.
   *
   * The reading carries `is_day`, but that is only true of the instant it was
   * taken: a dashboard opened at five in the afternoon would still be claiming
   * daylight at nine at night. The response also carries the day's sunrise and
   * sunset and the place's timezone, so the answer can be recomputed locally,
   * for free, for as long as the tab is open — no second fetch, no polling, and
   * no reliance on the reader's own clock or region.
   *
   * A minute is the right cadence: it is the resolution the solar bounds are
   * given in, and it costs one comparison.
   */
  const [minuteTick, setMinuteTick] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => setMinuteTick((n) => n + 1), 60_000)
    return () => clearInterval(timer)
  }, [])

  const night = useMemo(
    () => isNightFor(currentData),
    // `minuteTick` is not decoration: without it this memo would hold the
    // answer it computed at load until the next fetch, which is exactly what
    // "midnight flips it back to daytime" looks like from the inside.
    [currentData, minuteTick],
  )

  const scene = useMemo(
    () =>
      sceneForCondition({
        weatherCode: shown?.weather_code,
        riskLevel: shownRisk?.risk_level,
        hazard: shownRisk?.detected_hazard,
      }),
    [shown?.weather_code, shownRisk?.risk_level, shownRisk?.detected_hazard],
  )

  // What the next few hours hold, when they hold something worse than now. The
  // timeline is already fetched for the strip below; nothing extra is requested
  // to colour the sky with it.
  const approaching = useMemo(
    () => approachingScene(timelineData?.hours, scene),
    [timelineData?.hours, scene],
  )

  const themeKey = useMemo(
    () =>
      resolveTheme({
        weatherCode: shown?.weather_code,
        isDay: !night,
        riskLevel: shownRisk?.risk_level,
        hazard: shownRisk?.detected_hazard,
        appearance,
      }),
    [shown?.weather_code, night, shownRisk?.risk_level, shownRisk?.detected_hazard, appearance],
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
      // The risk map is on this page, so this is a scroll and not a journey.
      document.getElementById('risk-map')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    },
    [setMapFocus],
  )

  /**
   * Step two of the map's selection: the previewed place becomes *the* place.
   *
   * There is no separate location-detail page to send anyone to. The home page
   * is the destination, and it is already built to repaint itself around
   * whatever `location` holds — current conditions, risk, role advice, both
   * forecasts, the alert feed, the chat's context and the sky behind all of it
   * are keyed on it, so committing the location is the whole update.
   */
  /**
   * The map's selection, handed to the assistant as its subject.
   *
   * Committing the location is most of the work — every request the chat makes
   * carries `location`, so the answer is about the selected place from the next
   * turn onward. What that alone would not do is stop the *conversation* being
   * about somewhere else: the session memory on the server still holds the
   * previous place, and an assistant asked "and tomorrow?" would answer for it.
   *
   * So the session is dropped and the transcript cleared. Moving the subject is
   * a new conversation, not a turn in the old one, and the reader is told so by
   * the screen resetting rather than by an explanation.
   */
  const askAboutArea = useCallback(
    (entry) => {
      setLocation({
        name: entry.location,
        admin1: entry.admin1,
        latitude: entry.latitude,
        longitude: entry.longitude,
      })
      setSessionId(null)
      setMessages([])
      setChatError(null)
      setScreen('ai')
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    [setLocation, setSessionId],
  )

  const openLocalDetails = useCallback(
    (entry) => {
      setLocation({
        name: entry.location,
        admin1: entry.admin1,
        latitude: entry.latitude,
        longitude: entry.longitude,
      })
      setStage('app')
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    [setLocation],
  )

  return (
    <>
      <WeatherScene
        scene={scene}
        light={lightTheme}
        night={night}
        riskLevel={shownRisk?.risk_level}
        approaching={approaching}
        intensity={stage === 'app' ? 0.75 : 1}
      />

      {/* Greets the dashboard with the sky it just read. Reads the same payload
          the cards render, so it can never introduce a condition they disagree
          with, and it is deliberately absent from the landing page. */}
      <WeatherIntro data={currentData} selectedLocation={location?.name ?? null} active={stage === 'app'} />

      <AnimatePresence mode="wait">
        {stage === 'splash' && <SplashScreen key="splash" onDone={() => setStage('landing')} />}

        {stage === 'onboarding' && (
          <motion.div
            key="onboarding"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          >
            <Onboarding startAt={onboardAt} onDone={() => setStage('app')} />
          </motion.div>
        )}

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
              onEnter={() => { setOnboardAt('location'); setStage(onboarded ? 'app' : 'onboarding') }}
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
              /* Signing in re-enters the identity panel rather than opening a
                 separate modal: one flow, reachable from both places. */
              onSignIn={() => { setOnboardAt('identity'); setStage('onboarding') }}
            />

            {/* One <main> for all five destinations. They share the header, the
                store and the already-fetched response — switching tab changes
                what is rendered, never what has been loaded, so there is no
                second fetch and no flash of an empty screen. */}
            <main className="mx-auto w-full min-w-0 max-w-7xl space-y-3 px-3 pb-28 pt-3 sm:px-6 sm:pt-5">

              {/* ---------------- HOME — what should I do now? -------------
                  Home answers one question, and the order below *is* the
                  answer: what is happening, what to do about it, what it means
                  for you specifically, and where to ask more.

                  The map, the forecast and the alert list used to live here
                  too. They are not gone — each now has the destination it
                  deserves, reachable from the bar at the foot of the screen.
                  A page carrying every feature answers nothing first. ------ */}
              {screen === 'home' && (
                <>
                  {/* Level 0 when it fires: above even the conditions. */}
                  <EmergencyBanner
                    emergency={emergency}
                    audioBase64={answerHere?.audio_base64}
                    audioMime={answerHere?.audio_mime}
                  />

                  {/* 1 — What is happening now. */}
                  <CommandCenter
                    data={currentData}
                    loading={loading.current}
                    error={errors.current}
                    onRetry={refresh}
                    night={night}
                  />

                  {/* 2 — What to do about it. The single section this product
                      exists for, and the reason the reading above it is not
                      the top of the page. */}
                  <AdvisoryCard
                    advisory={advisory}
                    impacts={answerHere?.impacts?.length ? answerHere.impacts : currentData?.impacts}
                    onCompare={() => setCompareOpen(true)}
                  />

                  {/* 3 — What it means for whoever is reading. Derived from
                      this response's own bundle and risk, so it can never
                      disagree with the two cards above it. */}
                  <RoleIntelligence
                    intel={currentData?.role_intelligence}
                    loading={loading.current}
                    hours={timelineData?.hours}
                    bestTime={currentData?.personalization?.best_time}
                    // Whether an hour strip earns its space is a property of
                    // the role, and the role registry lives on the server.
                    timing={currentData?.personalization?.timing}
                  />

                  {/* 4 — Where to ask anything else. */}
                  <AskLauncher
                    onOpen={() => setScreen('ai')}
                    suggestions={currentData?.personalization?.suggested_questions}
                    onAsk={(query) => { setScreen('ai'); send(query) }}
                  />

                  {/* 5 — One line, and only when something is actually live.
                      An absence does not need a card. */}
                  <AlertIndicator onOpen={() => setScreen('alerts')} />

                  {/* A door to the map, not the map. */}
                  <MapLauncher ready={Boolean(mapData?.locations?.length)} onOpen={() => setScreen('map')} />
                </>
              )}

              {/* ---------------- AI — ask me anything -------------------- */}
              {screen === 'ai' && (
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
                  serverTranscribes={capabilities?.voice_input_available}
                  // Decided by the personalization engine from this same
                  // response, so the questions offered can only be about cards
                  // the reader is actually looking at.
                  suggestions={currentData?.personalization?.suggested_questions}
                />
              )}
              {/* How the last answer was built. It belongs beside the answer,
                  not on a page about the weather. */}
              {screen === 'ai' && <PipelinePanel answer={answerHere} />}

              {/* ---------------- MAP — where is the risk? ---------------- */}
              {screen === 'map' && (
                <>
                  <WeatherMap
                    tall
                    data={mapData}
                    hours={timelineData?.hours}
                    insights={timelineData?.insights}
                    loading={loading.map}
                    error={errors.map}
                    onAsk={askAboutArea}
                  />
                  {/* The risk view of the same country, with the two-step
                      selection that turns a marker into a reading and then into
                      a question. It left Home; it did not leave the product. */}
                  <RiskMap
                    data={mapData}
                    loading={loading.map}
                    error={errors.map}
                    onRetry={refresh}
                    onCommit={openLocalDetails}
                    onAsk={askAboutArea}
                  />
                </>
              )}

              {/* ---------------- ALERTS — what needs attention? ---------- */}
              {screen === 'alerts' && (
                <AlertsCenter
                  onViewArea={viewArea}
                  onSignIn={() => { setOnboardAt('identity'); setStage('onboarding') }}
                />
              )}

              {/* ---------------- FORECAST — what is coming? -------------- */}
              {screen === 'forecast' && (
                <>
                  <Timeline data={timelineData} loading={loading.timeline} error={errors.timeline} />
                  <Forecast data={forecastData} loading={loading.forecast} error={errors.forecast} />
                  {/* Trends: this place against its own record. Moved here from
                      Home, where it was the fourth thing competing to be read
                      and the first thing scrolled past. */}
                  <HistoricalContext similarity={similarity} />
                  <HistoricalNote comparison={similarity?.matched ? null : answerHere?.historical_comparison} />
                </>
              )}

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

            <BottomNav screen={screen} onNavigate={setScreen} />
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
 * The Home doorway into the assistant.
 *
 * The conversation has a destination of its own now, so what belongs on Home
 * is an invitation to it — stated as the question the reader can ask, not as
 * the name of a feature. Deliberately the same shape as `MapLauncher`: two
 * doors on the same page that behaved differently would read as two products.
 */
function AskLauncher({ onOpen, suggestions, onAsk }) {
  const language = useStore((s) => s.language)

  return (
    <section className="glass min-w-0 p-4">
      <h2 className="text-[10px] uppercase tracking-[0.14em] text-faint">
        {t(language, 'askAnything')}
      </h2>

      <button
        type="button"
        onClick={onOpen}
        className="mt-2 flex w-full min-w-0 items-center gap-3 rounded-[var(--radius-card)]
                   border border-[var(--wx-border)] bg-[var(--wx-bg)] px-3.5 py-3 text-left
                   transition hover:border-primary/50"
      >
        <span aria-hidden="true" className="shrink-0 text-[15px] text-primary">✦</span>
        <span className="min-w-0 flex-1 truncate text-[13px] text-muted">
          {t(language, 'placeholder')}
        </span>
        <span aria-hidden="true" className="shrink-0 text-[15px] text-muted">🎙</span>
      </button>

      {/* The server's own suggestions, and only for cards the reader is
          actually looking at. Tapping one opens the assistant with the question
          already asked, rather than opening an empty conversation. */}
      {suggestions?.length > 0 && (
        <ul className="mt-2.5 flex min-w-0 flex-wrap gap-1.5">
          {suggestions.slice(0, 4).map((item) => (
            <li key={item.id} className="min-w-0">
              <button
                type="button"
                onClick={() => onAsk?.(item.query)}
                className="max-w-full truncate rounded-[var(--radius-pill)] border border-[var(--wx-border)]
                           bg-[var(--wx-bg)] px-3 py-1.5 text-[11.5px] font-medium text-ink-soft
                           transition hover:border-primary/50 hover:text-ink"
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      )}

      <button
        type="button"
        onClick={onOpen}
        className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-[var(--radius-card)]
                   bg-primary px-4 py-2.5 text-[13px] font-semibold text-white
                   transition hover:brightness-110"
      >
        {t(language, 'openAssistant')}
        <span aria-hidden="true">→</span>
      </button>
    </section>
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
