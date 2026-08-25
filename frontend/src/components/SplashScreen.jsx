import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { useReducedMotion } from '../hooks/useReducedMotion'

/**
 * Application-entry splash.
 *
 * The official WeatherGPT logo is the hero and is rendered as-is: one <img>,
 * aspect ratio untouched, never cropped or stretched, and never decomposed into
 * separately animated parts. Everything that moves here is *around* the logo —
 * the atmosphere it emerges from and the glow that settles behind it — so the
 * mark itself stays exactly as supplied.
 *
 * Choreography (≈4.1s total):
 *   1. atmosphere  600ms   background and glow fade up
 *   2. logo        800ms   fades in, 94% → 100%
 *   3. emphasis    900ms   glow expands and settles behind the mark
 *   4. hold       1200ms   enough to read the wordmark and the tagline
 *   5. exit        600ms   fades up into the landing page
 *
 * Reduced motion collapses this to a plain fade in / hold / fade out with no
 * scaling and no sweep.
 */

/**
 * Served from `public/`, so a missing file degrades to the wordmark fallback
 * below instead of failing the build. Drop the official artwork in at:
 *
 *     frontend/public/weathergpt-logo.png
 */
export const LOGO_SRC = '/weathergpt-logo.png'

// Warm the asset as early as the module is evaluated, so phase 2 fades in a
// decoded image rather than an empty box.
if (typeof window !== 'undefined') {
  const preload = new Image()
  preload.src = LOGO_SRC
}

const TIMINGS = {
  atmosphere: 600,
  logo: 800,
  emphasis: 900,
  hold: 1200,
  exit: 600,
}

const REDUCED = { in: 400, hold: 1200, exit: 400 }

export default function SplashScreen({ onDone }) {
  const reduced = useReducedMotion()
  const [leaving, setLeaving] = useState(false)
  const [logoState, setLogoState] = useState('loading') // loading | ready | missing

  // `onDone` is a fresh closure on every parent render, and the parent
  // re-renders several times while the dashboard's first requests land. Holding
  // it in a ref keeps the timeline anchored to mount: without this the timers
  // restart on each render and the splash drifts past its budget.
  const onDoneRef = useRef(onDone)
  useEffect(() => {
    onDoneRef.current = onDone
  }, [onDone])

  useEffect(() => {
    const total = reduced
      ? REDUCED.in + REDUCED.hold + REDUCED.exit
      : TIMINGS.atmosphere + TIMINGS.logo + TIMINGS.emphasis + TIMINGS.hold + TIMINGS.exit
    const exitAt = total - (reduced ? REDUCED.exit : TIMINGS.exit)

    const leaveTimer = setTimeout(() => setLeaving(true), exitAt)
    const doneTimer = setTimeout(() => onDoneRef.current?.(), total)
    return () => {
      clearTimeout(leaveTimer)
      clearTimeout(doneTimer)
    }
  }, [reduced])

  // Phase 2 starts once the atmosphere has established itself.
  const logoDelay = reduced ? 0.05 : TIMINGS.atmosphere / 1000
  const emphasisDelay = reduced ? 0 : (TIMINGS.atmosphere + TIMINGS.logo) / 1000

  return (
    <motion.div
      role="status"
      aria-label="WeatherGPT"
      initial={{ opacity: 0 }}
      animate={{ opacity: leaving ? 0 : 1 }}
      transition={{
        duration: leaving ? (reduced ? REDUCED.exit : TIMINGS.exit) / 1000 : 0.45,
        ease: 'easeInOut',
      }}
      className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden"
      style={{
        // Light, weather-inspired ground: white lifting into a soft sky blue.
        background: 'linear-gradient(180deg, #ffffff 0%, #f5fbff 46%, #e6f3fd 100%)',
      }}
    >
      {/* Atmosphere. Sits behind the logo and never over it. */}
      <motion.div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: TIMINGS.atmosphere / 1000, ease: 'easeOut' }}
        style={{
          background:
            'radial-gradient(58% 44% at 50% 42%, rgb(34 211 238 / 0.10), transparent 68%),' +
            'radial-gradient(46% 34% at 22% 74%, rgb(96 165 250 / 0.09), transparent 70%),' +
            'radial-gradient(40% 30% at 82% 26%, rgb(45 212 191 / 0.07), transparent 72%)',
        }}
      />

      {/* Phase 3: a soft glow expands once and settles. The logo does not move. */}
      {!reduced && (
        <motion.div
          aria-hidden="true"
          className="pointer-events-none absolute rounded-full"
          style={{
            width: 'min(78vw, 620px)',
            height: 'min(78vw, 620px)',
            background:
              'radial-gradient(circle, rgb(34 211 238 / 0.20) 0%, rgb(56 189 248 / 0.09) 42%, transparent 68%)',
            filter: 'blur(16px)',
          }}
          initial={{ opacity: 0, scale: 0.72 }}
          animate={{ opacity: [0, 0.85, 0.5], scale: [0.72, 1.06, 1] }}
          transition={{
            duration: TIMINGS.emphasis / 1000,
            delay: emphasisDelay,
            ease: [0.22, 1, 0.36, 1],
            times: [0, 0.62, 1],
          }}
        />
      )}

      {/* Phase 2: the official mark, whole and unaltered. */}
      <motion.div
        className="relative flex w-full items-center justify-center px-6"
        initial={{ opacity: 0, scale: reduced ? 1 : 0.94 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{
          duration: (reduced ? REDUCED.in : TIMINGS.logo) / 1000,
          delay: logoDelay,
          ease: [0.22, 1, 0.36, 1],
        }}
      >
        <AnimatePresence mode="wait">
          {logoState === 'missing' ? (
            <WordmarkFallback key="fallback" />
          ) : (
            <img
              key="logo"
              src={LOGO_SRC}
              alt="WeatherGPT — Conversational Weather Intelligence"
              onLoad={() => setLogoState('ready')}
              onError={() => setLogoState('missing')}
              // Intrinsic ratio is preserved: width is clamped, height follows.
              className="h-auto w-full select-none object-contain"
              style={{ maxWidth: 'min(86vw, 520px)', maxHeight: '78vh' }}
              draggable="false"
              decoding="async"
              fetchPriority="high"
            />
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  )
}

/**
 * Shown only when the logo file is absent.
 *
 * This is a safety net, not a substitute mark: it reuses the wordmark the app
 * already renders in its header so a missing asset degrades quietly instead of
 * showing a broken image.
 */
function WordmarkFallback() {
  useEffect(() => {
    if (import.meta.env.DEV) {
      console.warn(
        `[WeatherGPT] Splash logo not found at ${LOGO_SRC}. ` +
          'Add the official artwork to frontend/public/weathergpt-logo.png.',
      )
    }
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex flex-col items-center text-center"
    >
      <div
        className="text-4xl font-semibold tracking-tight sm:text-5xl"
        style={{ fontFamily: 'var(--font-display)', color: '#0b2a52' }}
      >
        Weather<span style={{ color: '#22a7d8' }}>GPT</span>
      </div>
      <p
        className="mt-2.5 text-[11px] font-medium uppercase tracking-[0.28em]"
        style={{ color: '#5b7fa6' }}
      >
        Conversational Weather Intelligence
      </p>
    </motion.div>
  )
}
