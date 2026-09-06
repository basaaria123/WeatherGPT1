import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { CONDITION, normalizeCondition } from '../theme/weatherTheme'
import WeatherGlyph from './ui/WeatherGlyph'
import { Cloud, Drops, Lightning, Motes, Sun, Veils } from './intro/IntroLayers'
import { scaleForViewport, variantFor } from './intro/introVariants'

/**
 * The weather intro.
 *
 * For about two seconds when the dashboard opens, and again whenever the user
 * lands on a new place, WeatherGPT shows the sky it just read before showing
 * the numbers it read from it. It is a greeting, not a loading screen: the
 * overlay never takes a pointer event, the dashboard is already mounted and
 * live behind it, and it leaves on its own.
 *
 * Everything it draws comes from the payload the dashboard itself renders —
 * the same `weather_code` through the same `normalizeCondition()`, and the
 * caption is the backend's own already-translated `condition` string. There is
 * no second reading of the weather here, so the intro cannot contradict the
 * card that follows it.
 *
 * Two rules keep it from ever showing the wrong sky:
 *
 *   1. A payload only counts when its own `location` is the place currently
 *      selected. `App` already drops responses that arrive after the selection
 *      moved on; this is the second, independent check, so a stale Guwahati
 *      response can never introduce Delhi.
 *   2. It plays once per place. A language switch, a profile switch or a
 *      refresh all refetch the same location, and none of them replays it.
 */

// Roughly two seconds from first pixel to gone: long enough to register as a
// deliberate moment, short enough that nobody waits through it.
const TIMINGS = { full: 1950, reduced: 1100 }

/**
 * How long the app takes to arrive.
 *
 * `App` crossfades the landing page out and the dashboard in, about 0.45s
 * each. `stage` flips to 'app' at the start of that, so an intro fired
 * immediately would spend most of its two seconds playing over a half-faded
 * landing page — visible where it must not be, and gone by the time the
 * dashboard it is introducing has arrived. It waits for the handover instead.
 */
const APP_ENTRANCE_MS = 780

export default function WeatherIntro({ data, selectedLocation, active }) {
  const reduced = useReducedMotion()
  const [play, setPlay] = useState(null)
  const playedFor = useRef(null)

  // The payload is only usable while it is describing the place on screen.
  const resolvedName = data?.location?.name ?? null
  const matches = Boolean(active && resolvedName && resolvedName === selectedLocation)
  const current = matches ? data.current : null

  // False until the dashboard has actually finished arriving. A location change
  // happens with it already on screen, so this is only ever a gate on entry.
  const [arrived, setArrived] = useState(false)

  useEffect(() => {
    if (!active) {
      setArrived(false)
      return undefined
    }
    const timer = window.setTimeout(() => setArrived(true), APP_ENTRANCE_MS)
    return () => window.clearTimeout(timer)
  }, [active])

  useEffect(() => {
    if (!active) {
      // Leaving the dashboard resets the memory, so coming back in is an
      // opening again and gets its greeting.
      playedFor.current = null
      setPlay(null)
      return undefined
    }
    if (!arrived) return undefined
    if (!matches || !current) return undefined
    if (playedFor.current === resolvedName) return undefined

    playedFor.current = resolvedName
    setPlay({
      id: `${resolvedName}:${Date.now()}`,
      condition: normalizeCondition(current.weather_code),
      code: current.weather_code,
      // The backend's own words, in the user's own language. Nothing here is
      // generated, and an absent condition simply means no caption.
      label: current.condition ?? null,
      temperature: typeof current.temperature_c === 'number' ? Math.round(current.temperature_c) : null,
      place: resolvedName,
    })
    return undefined
  }, [active, arrived, matches, current, resolvedName])

  /**
   * The dismissal, deliberately in its own effect keyed to the running intro.
   *
   * Sharing the effect above would tie the timer to `current`, whose identity
   * changes whenever anything refetches this location — switching language
   * mid-intro would cancel the timer and leave the overlay up for good.
   * Keyed to `play.id`, it re-arms only when a genuinely new intro starts.
   */
  useEffect(() => {
    if (!play) return undefined
    const timer = window.setTimeout(() => setPlay(null), reduced ? TIMINGS.reduced : TIMINGS.full)
    return () => window.clearTimeout(timer)
  }, [play, reduced])

  return (
    <AnimatePresence>
      {play && <IntroOverlay key={play.id} play={play} reduced={reduced} />}
    </AnimatePresence>
  )
}

function IntroOverlay({ play, reduced }) {
  const variant = useMemo(() => {
    const base = variantFor(play.condition)
    if (reduced) {
      // Reduced motion keeps the atmosphere and drops the movement: no falling
      // particles, no drifting banks, no lightning.
      return { ...base, drops: null, clouds: [], veils: 0, motes: 0, flashes: [] }
    }
    return scaleForViewport(base, typeof window === 'undefined' ? 1280 : window.innerWidth)
  }, [play.condition, reduced])

  const known = play.condition !== CONDITION.UNKNOWN
  const fade = reduced ? 0.28 : 0.45

  return (
    <motion.div
      aria-hidden="true"
      data-weather-intro={play.condition}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: reduced ? 0.2 : 0.24, exit: { duration: fade } }}
      /* Above the dashboard for its two seconds and below the header's own
         menus, and transparent to the pointer throughout — the dashboard
         underneath stays fully usable while this plays. */
      className="pointer-events-none fixed inset-0 z-40 overflow-hidden"
    >
      {/* The wash. Tinted with the condition's accent over the theme's own
          scrim, so it darkens a night sky and lightens a bright one instead of
          fighting whichever theme is active. */}
      <div
        className="absolute inset-0"
        style={{
          background: `radial-gradient(120% 90% at 50% 18%,
            color-mix(in srgb, ${variant.accent} ${Math.round(variant.wash * 100)}%, transparent) 0%,
            transparent 62%), rgb(var(--wx-scrim) / ${reduced ? 0.34 : 0.46})`,
          backdropFilter: reduced ? 'none' : 'blur(2px)',
        }}
      />

      {variant.sun && <Sun spec={variant.sun} accent={variant.accent} />}
      {variant.clouds.map((cloud, index) => (
        <Cloud key={index} spec={cloud} index={index} accent={variant.accent} />
      ))}
      {variant.veils > 0 && <Veils count={variant.veils} accent={variant.accent} />}
      {variant.drops && <Drops spec={variant.drops} accent={variant.accent} />}
      {variant.motes > 0 && <Motes count={variant.motes} accent={variant.accent} />}
      {variant.flashes.length > 0 && <Lightning flashes={variant.flashes} />}

      {/* The caption names the condition and nothing else. It appears only when
          the payload actually carried one — an unreadable sky gets the wash and
          no words, rather than a guess. */}
      {known && play.label && (
        // The outer element does the centring and the inner one does the
        // motion: framer writes its own `transform`, which would otherwise
        // overwrite a Tailwind translate and leave the caption off-centre.
        <div className="absolute inset-0 flex items-center justify-center px-6">
          <motion.div
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: reduced ? 0.08 : 0.3, duration: reduced ? 0.2 : 0.5, ease: [0.22, 1, 0.36, 1] }}
            className="relative flex flex-col items-center text-center"
          >
            {/* A soft pool of the theme's own scrim, so the words stay legible
                whatever the card behind them happens to say. */}
            <div
              aria-hidden="true"
              className="pointer-events-none absolute left-1/2 top-1/2 h-[260px] w-[560px] max-w-[92vw]
                         -translate-x-1/2 -translate-y-1/2"
              style={{
                background: `radial-gradient(closest-side, rgb(var(--wx-scrim) / 0.72), transparent 78%)`,
              }}
            />
            <div className="relative flex items-center gap-2.5">
              {/* The dashboard's own glyph, so the picture above the words is
                  the same picture the hero card shows a moment later. */}
              <WeatherGlyph code={play.code} size={34} />
              <span
                className="text-[clamp(1.35rem,5.5vw,2rem)] font-semibold tracking-tight text-ink"
                style={{ fontFamily: 'var(--font-display)' }}
              >
                {play.temperature !== null && <span className="tabular-nums">{play.temperature}° · </span>}
                {play.label}
              </span>
            </div>
            <span className="relative mt-1 text-[11px] uppercase tracking-[0.22em] text-muted">{play.place}</span>
          </motion.div>
        </div>
      )}
    </motion.div>
  )
}
