import { motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { isLatinText } from '../i18n/scriptSupport'
import { t } from '../i18n/ui'

/**
 * Which way the wind is blowing, and how hard.
 *
 * The reading comes from the payload the dashboard already fetched — the same
 * `wind_speed_kmh` and `wind_direction_deg` the metric grid above it prints —
 * so the dial and the numbers can never disagree, and no second request is made
 * for them.
 *
 * Meteorological convention: `wind_direction_deg` is the direction the wind
 * blows *from*. The needle points that way, like a weather vane, and the label
 * names that origin — a "NE wind" is one arriving from the northeast.
 */

const POINTS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']

/**
 * Degrees to one of the eight cardinal points.
 *
 * Each point owns a 45° arc centred on its own bearing, so north spans 337.5°
 * through 22.5° and the rounding is symmetric rather than biased clockwise.
 * Returns null for anything that is not a usable number, because "no reading"
 * has to stay distinguishable from "north".
 */
export function compassPoint(degrees) {
  if (degrees === null || degrees === undefined) return null
  const value = Number(degrees)
  if (!Number.isFinite(value)) return null
  const normalised = ((value % 360) + 360) % 360
  return POINTS[Math.round(normalised / 45) % 8]
}

/**
 * The rotation to animate to, given where the needle already is.
 *
 * Angles are kept as a running total rather than reset into 0–360, because a
 * needle at 350° asked to show 10° would otherwise sweep 340° backwards around
 * the dial. Folding the difference into ±180° turns that into the 20° nudge a
 * real vane would make.
 */
export function shortestRotation(from, to) {
  const delta = (((to - from) % 360) + 540) % 360 - 180
  return from + delta
}

export default function WeatherCompass({ current, language, userType }) {
  const reduced = useReducedMotion()

  const degrees = current?.wind_direction_deg
  const point = compassPoint(degrees)
  const speed = typeof current?.wind_speed_kmh === 'number' ? current.wind_speed_kmh : null
  const gust = typeof current?.wind_gust_kmh === 'number' ? current.wind_gust_kmh : null

  // The needle's absolute rotation, accumulated so it never unwinds the long
  // way round. Held in a ref because it is animation state, not display state.
  const angleRef = useRef(0)
  const [angle, setAngle] = useState(0)

  useEffect(() => {
    if (point === null) return
    const next = shortestRotation(angleRef.current, ((Number(degrees) % 360) + 360) % 360)
    angleRef.current = next
    setAngle(next)
  }, [degrees, point])

  const heading = t(language, 'windLabels')?.[userType] ?? t(language, 'wind')

  return (
    <div className="flex items-center gap-4 sm:gap-5">
      <Dial angle={angle} known={point !== null} reduced={reduced} calm={speed === 0} />

      <div className="min-w-0">
        {/* Uppercase and letter-spacing are Latin devices; applied to Devanagari
            or Telugu the extra tracking pulls conjuncts apart. */}
        <div
          className={`text-[11px] text-faint ${
            isLatinText(heading) ? 'uppercase tracking-[0.12em]' : 'text-[12px]'
          }`}
        >
          {heading}
        </div>

        <div className="mt-0.5 flex items-baseline gap-1">
          {speed === null ? (
            <span className="text-xl font-semibold tabular-nums text-muted">—</span>
          ) : (
            <>
              <span className="text-xl font-semibold tabular-nums text-ink">{Math.round(speed)}</span>
              <span className="text-[11px] text-muted">km/h</span>
            </>
          )}
        </div>

        <div className="mt-1 text-[12px] text-ink-soft">
          <span className="text-muted">{t(language, 'direction')}: </span>
          {/* Never a guessed bearing: an absent reading says so in words. */}
          {point === null ? (
            <span className="text-faint">{t(language, 'unavailable')}</span>
          ) : speed === 0 ? (
            <span className="text-faint">{t(language, 'calm')}</span>
          ) : (
            <span className="font-semibold text-primary">{point}</span>
          )}
        </div>

        {gust !== null && speed !== null && gust > speed && (
          <div className="mt-0.5 text-[11px] text-faint">
            {t(language, 'gusts')} {Math.round(gust)} km/h
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * The dial.
 *
 * Inline SVG so it inherits the theme's colours and stays crisp at any size.
 * Nothing on it animates on its own — the needle moves when the wind reading
 * changes and is otherwise perfectly still.
 */
function Dial({ angle, known, reduced, calm }) {
  return (
    <svg
      width="92"
      height="92"
      viewBox="0 0 100 100"
      className="shrink-0"
      role="img"
      aria-label={known ? `Wind direction dial` : `Wind direction unavailable`}
    >
      <circle cx="50" cy="50" r="43" fill="rgb(var(--wx-tint) / 0.035)" stroke="rgb(var(--wx-tint) / 0.12)" />
      <circle cx="50" cy="50" r="33" fill="none" stroke="rgb(var(--wx-tint) / 0.07)" />

      {/* Ticks: the four cardinals long, the four intercardinals short. */}
      {POINTS.map((name, index) => {
        const long = index % 2 === 0
        return (
          <line
            key={name}
            x1="50"
            y1={long ? 11 : 13}
            x2="50"
            y2={long ? 18 : 16.5}
            stroke="rgb(var(--wx-tint) / 0.3)"
            strokeWidth={long ? 1.6 : 1.1}
            strokeLinecap="round"
            transform={`rotate(${index * 45} 50 50)`}
          />
        )
      })}

      <text
        x="50"
        y="9.5"
        textAnchor="middle"
        fontSize="10"
        fontWeight="700"
        fill="var(--color-primary)"
        letterSpacing="0.5"
      >
        N
      </text>
      {[['E', 95.5, 53.5], ['S', 50, 97.5], ['W', 4.5, 53.5]].map(([label, x, y]) => (
        <text key={label} x={x} y={y} textAnchor="middle" fontSize="8.5" fill="var(--color-faint)">
          {label}
        </text>
      ))}

      {known ? (
        <motion.g
          animate={{ rotate: angle }}
          // A vane settles rather than snaps; reduced motion skips the travel
          // and simply shows the new bearing.
          transition={reduced ? { duration: 0 } : { type: 'spring', stiffness: 70, damping: 14, mass: 0.9 }}
          // `transform-origin` in the SVG's own user units. Framer's originX /
          // originY do not reach an SVG group, and the default origin of (0,0)
          // swings the needle clean out of the viewBox.
          style={{ transformOrigin: '50px 50px', transformBox: 'view-box' }}
        >
          {/* The lit half points into the wind; the tail is dimmed so the
              needle reads as directional at a glance. */}
          <path d="M50 20 L56 52 L50 47 L44 52 Z" fill="var(--color-primary)" />
          <path d="M50 80 L44 50 L50 54 L56 50 Z" fill="rgb(var(--wx-tint) / 0.22)" />
        </motion.g>
      ) : (
        // Neutral state: a hub and no needle, so nothing implies a bearing.
        <circle cx="50" cy="50" r="15" fill="none" stroke="rgb(var(--wx-tint) / 0.1)" strokeDasharray="3 4" />
      )}

      <circle
        cx="50"
        cy="50"
        r="3.4"
        fill={calm || !known ? 'rgb(var(--wx-tint) / 0.25)' : 'var(--color-primary)'}
      />
    </svg>
  )
}
