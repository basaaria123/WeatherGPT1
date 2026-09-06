import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { CONDITION, normalizeCondition } from '../theme/weatherTheme'
import { Cloud, Drops, Lightning, Motes, Sun, Veils } from './intro/IntroLayers'
import { scaleForBurst, variantFor } from './intro/introVariants'

/**
 * Tap the weather icon and the card shows you that weather for a second.
 *
 * It is the intro animation at card scale, from the same recipe: the condition
 * comes from `normalizeCondition()` on the same `weather_code` the icon beside
 * it was drawn from, and the visual comes from `variantFor()`. Two surfaces,
 * one description of what rain looks like — which is what stops them drifting
 * into disagreeing about the sky.
 *
 * It fills its positioned parent, never takes a pointer event, and unmounts
 * when it finishes, so nothing keeps animating in a card nobody is looking at.
 */

const DURATION = { full: 1100, reduced: 420 }

export default function WeatherMicroBurst({ token, weatherCode }) {
  const reduced = useReducedMotion()
  const [playing, setPlaying] = useState(false)
  const hostRef = useRef(null)
  const [height, setHeight] = useState(0)

  const condition = normalizeCondition(weatherCode)
  // An unreadable sky gets no burst at all. Showing the nearest weather it
  // resembles would be inventing a reading the dashboard never made.
  const known = condition !== CONDITION.UNKNOWN

  useEffect(() => {
    if (!token || !known) return undefined
    setPlaying(true)
    const timer = window.setTimeout(() => setPlaying(false), reduced ? DURATION.reduced : DURATION.full)
    return () => window.clearTimeout(timer)
  }, [token, known, reduced])

  // Drops need a real distance to fall: inside a card, a viewport-height
  // travel would put them past the bottom before they were ever seen.
  useLayoutEffect(() => {
    if (!playing || !hostRef.current) return
    setHeight(hostRef.current.offsetHeight)
  }, [playing])

  const variant = playing ? scaleForBurst(variantFor(condition)) : null

  return (
    <AnimatePresence>
      {playing && variant && (
        <motion.div
          ref={hostRef}
          aria-hidden="true"
          data-weather-burst={condition}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduced ? 0.14 : 0.22 }}
          /* A positioned child at z-index 0 paints above the card's in-flow
             text. Negative z puts the weather above the card's background and
             behind every word on it, which is where it belongs. */
          className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
        >
          {/* A breath of the condition's colour, so even the reduced-motion
              path reads as a response to the tap rather than nothing. */}
          <div
            className="absolute inset-0"
            style={{
              background: `radial-gradient(80% 70% at 22% 30%,
                color-mix(in srgb, ${variant.accent} 12%, transparent) 0%, transparent 64%)`,
            }}
          />

          {!reduced && (
            <>
              {variant.sun && <Sun spec={variant.sun} accent={variant.accent} />}
              {variant.clouds.map((cloud, index) => (
                <Cloud key={index} spec={cloud} index={index} accent={variant.accent} />
              ))}
              {variant.veils > 0 && <Veils count={variant.veils} accent={variant.accent} />}
              {variant.drops && height > 0 && (
                <Drops spec={variant.drops} accent={variant.accent} distance={height} />
              )}
              {variant.motes > 0 && <Motes count={variant.motes} accent={variant.accent} />}
              {variant.flashes.length > 0 && <Lightning flashes={variant.flashes} />}
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
