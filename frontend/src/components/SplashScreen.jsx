import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { useReducedMotion } from '../hooks/useReducedMotion'

/**
 * Branded splash: data particles converge into the wordmark.
 *
 * It is a build-in, not a spinner — the motion says "readings resolving into an
 * answer", which is the product's whole thesis. Reduced motion gets a plain
 * fade of the same mark at the same duration, so nothing jumps.
 */

const PARTICLES = 26

export default function SplashScreen({ onDone, duration = 3400 }) {
  const reduced = useReducedMotion()
  const [leaving, setLeaving] = useState(false)

  useEffect(() => {
    const total = reduced ? 1400 : duration
    const leaveTimer = setTimeout(() => setLeaving(true), total - 500)
    const doneTimer = setTimeout(onDone, total)
    return () => {
      clearTimeout(leaveTimer)
      clearTimeout(doneTimer)
    }
  }, [onDone, duration, reduced])

  const particles = Array.from({ length: PARTICLES }).map((_, index) => {
    const angle = (index / PARTICLES) * Math.PI * 2
    const radius = 130 + (index % 5) * 34
    return {
      id: index,
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius * 0.62,
      delay: 0.05 * (index % 8),
    }
  })

  return (
    <motion.div
      role="status"
      aria-label="WeatherGPT is starting"
      initial={{ opacity: 1 }}
      animate={{ opacity: leaving ? 0 : 1 }}
      transition={{ duration: 0.5, ease: 'easeInOut' }}
      className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden"
      style={{
        background:
          'radial-gradient(120% 100% at 50% 30%, #0a2647 0%, #050d1a 55%, #030814 100%)',
      }}
    >
      {!reduced && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          {particles.map((particle) => (
            <motion.span
              key={particle.id}
              className="absolute h-1.5 w-1.5 rounded-full"
              style={{ background: particle.id % 3 === 0 ? '#2dd4bf' : '#22d3ee' }}
              initial={{ x: particle.x, y: particle.y, opacity: 0, scale: 0.5 }}
              animate={{
                x: [particle.x, particle.x * 0.35, 0],
                y: [particle.y, particle.y * 0.35, 0],
                opacity: [0, 0.95, 0],
                scale: [0.5, 1, 0.3],
              }}
              transition={{
                duration: 1.9,
                delay: particle.delay,
                ease: [0.4, 0, 0.2, 1],
                times: [0, 0.55, 1],
              }}
            />
          ))}
        </div>
      )}

      <div className="relative flex flex-col items-center px-6 text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, delay: reduced ? 0.1 : 1.15, ease: [0.22, 1, 0.36, 1] }}
          className="mb-5"
        >
          <Mark />
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: reduced ? 0.15 : 1.35, ease: [0.22, 1, 0.36, 1] }}
          className="text-4xl font-semibold tracking-tight text-ink sm:text-5xl"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          Weather<span className="text-primary">GPT</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: reduced ? 0.25 : 1.7 }}
          className="mt-2.5 text-[11px] font-medium uppercase tracking-[0.34em] text-muted"
        >
          Weather Intelligence
        </motion.p>

        {/* A thin progress rule reads as deliberate; a browser spinner does not. */}
        <motion.div
          className="mt-8 h-px w-40 origin-left bg-gradient-to-r from-transparent via-primary to-transparent"
          initial={{ scaleX: 0, opacity: 0 }}
          animate={{ scaleX: 1, opacity: 1 }}
          transition={{ duration: reduced ? 1.1 : 2.4, ease: 'easeInOut' }}
        />
      </div>
    </motion.div>
  )
}

function Mark() {
  return (
    <svg width="64" height="64" viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <circle cx="32" cy="32" r="30" stroke="#22d3ee" strokeOpacity="0.28" strokeWidth="1.5" />
      <path
        d="M17 38a9 9 0 0 1 2.2-17.7 13 13 0 0 1 24.6 3.4A8.5 8.5 0 0 1 45 38Z"
        fill="#22d3ee"
        fillOpacity="0.2"
        stroke="#22d3ee"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M25 43l-2.5 7M33 43l-2.5 7M41 43l-2.5 7" stroke="#2dd4bf" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  )
}
