import { motion } from 'framer-motion'
import { useReducedMotion } from '../../hooks/useReducedMotion'

/**
 * Condition glyph.
 *
 * Drawn as inline SVG rather than an emoji or a cartoon set: it inherits the
 * palette, stays crisp at any size, and its motion can be switched off cleanly
 * for reduced-motion users.
 */
const SCENE_BY_CODE = (code) => {
  if (code === null || code === undefined) return 'clear'
  const value = Number(code)
  if ([0, 1].includes(value)) return 'clear'
  if ([2, 3].includes(value)) return 'cloudy'
  if ([45, 48].includes(value)) return 'fog'
  if ([95, 96, 99, 82].includes(value)) return 'storm'
  if (value >= 71 && value <= 86) return 'snow'
  if (value >= 51) return 'rain'
  return 'clear'
}

export function sceneForCode(code) {
  return SCENE_BY_CODE(code)
}

export default function WeatherGlyph({ code, size = 72, className = '' }) {
  const reduced = useReducedMotion()
  const scene = SCENE_BY_CODE(code)
  const drift = reduced ? {} : { animate: { x: [0, 3, 0] }, transition: { duration: 7, repeat: Infinity, ease: 'easeInOut' } }

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      className={className}
      role="img"
      aria-label={`Weather condition: ${scene}`}
    >
      {(scene === 'clear' || scene === 'fog') && (
        <motion.g
          animate={reduced ? undefined : { rotate: 360 }}
          transition={reduced ? undefined : { duration: 90, repeat: Infinity, ease: 'linear' }}
          style={{ originX: '50%', originY: '50%' }}
        >
          <circle cx="32" cy="30" r="11" fill="var(--color-caution)" opacity="0.9" />
          {Array.from({ length: 8 }).map((_, index) => (
            <rect
              key={index}
              x="31"
              y="8"
              width="2"
              height="6"
              rx="1"
              fill="var(--color-caution)"
              opacity="0.55"
              transform={`rotate(${index * 45} 32 30)`}
            />
          ))}
        </motion.g>
      )}

      {scene !== 'clear' && (
        <motion.g {...drift}>
          <ellipse cx="27" cy="30" rx="15" ry="10" fill="var(--color-accent)" opacity="0.34" />
          <ellipse cx="39" cy="27" rx="12" ry="9" fill="var(--color-ink-soft)" opacity="0.26" />
        </motion.g>
      )}

      {(scene === 'rain' || scene === 'storm') &&
        [22, 32, 42].map((x, index) => (
          <motion.line
            key={x}
            x1={x}
            y1="42"
            x2={x - 3}
            y2="53"
            stroke="var(--color-primary)"
            strokeWidth="2.2"
            strokeLinecap="round"
            opacity="0.8"
            animate={reduced ? undefined : { y: [0, 7], opacity: [0.8, 0] }}
            transition={
              reduced ? undefined : { duration: 1.05, repeat: Infinity, delay: index * 0.28, ease: 'easeIn' }
            }
          />
        ))}

      {scene === 'storm' && (
        <motion.path
          d="M34 38 L28 49 H33 L30 58 L40 46 H34.5 L38 38 Z"
          fill="var(--color-caution)"
          animate={reduced ? { opacity: 0.95 } : { opacity: [0.25, 1, 0.35, 1, 0.3] }}
          transition={reduced ? undefined : { duration: 3.2, repeat: Infinity, times: [0, 0.08, 0.16, 0.24, 1] }}
        />
      )}

      {scene === 'snow' &&
        [23, 32, 41].map((x, index) => (
          <motion.circle
            key={x}
            cx={x}
            cy="46"
            r="2.2"
            fill="var(--color-ink)"
            opacity="0.75"
            animate={reduced ? undefined : { y: [0, 9], opacity: [0.75, 0] }}
            transition={reduced ? undefined : { duration: 2.4, repeat: Infinity, delay: index * 0.5 }}
          />
        ))}

      {scene === 'fog' &&
        [44, 49, 54].map((y, index) => (
          <motion.line
            key={y}
            x1="16"
            y1={y}
            x2="48"
            y2={y}
            stroke="var(--color-ink-soft)"
            strokeWidth="2.6"
            strokeLinecap="round"
            opacity="0.4"
            animate={reduced ? undefined : { x: [0, 4, 0] }}
            transition={reduced ? undefined : { duration: 5 + index, repeat: Infinity, ease: 'easeInOut' }}
          />
        ))}
    </svg>
  )
}
