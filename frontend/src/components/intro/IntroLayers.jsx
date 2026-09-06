import { useEffect, useState } from 'react'
import { scatter } from './introVariants'

/**
 * The pieces the weather intro is built from.
 *
 * Every one of them is a handful of absolutely positioned elements running a
 * CSS keyframe — no canvas, no particle engine, no library. The whole overlay
 * unmounts when the intro ends, so the animation work stops with it rather
 * than idling behind the dashboard.
 *
 * Colour comes from theme variables only, so the intro follows whatever the
 * weather theme has set rather than carrying its own palette.
 */

/** A soft warm disc with a bloom. Clear and partly-cloudy skies only. */
export function Sun({ spec, accent }) {
  return (
    <div
      className="wx-intro-sun pointer-events-none absolute"
      style={{
        top: '26%',
        left: '50%',
        width: spec.size,
        height: spec.size,
        marginLeft: -spec.size / 2,
        marginTop: -spec.size / 2,
        background: `radial-gradient(circle at 50% 50%,
          color-mix(in srgb, ${accent} 85%, transparent) 0%,
          color-mix(in srgb, ${accent} 42%, transparent) 26%,
          color-mix(in srgb, ${accent} 12%, transparent) 52%,
          transparent 72%)`,
        opacity: spec.glow,
      }}
    />
  )
}

/** One soft bank, blurred well past its edges so it reads as air, not a shape. */
export function Cloud({ spec, index, accent }) {
  const width = 380 * spec.size
  const height = 112 * spec.size
  return (
    <div
      className="wx-intro-cloud pointer-events-none absolute"
      style={{
        top: `${spec.top}%`,
        left: '50%',
        width,
        height,
        marginLeft: -width / 2,
        background: `radial-gradient(60% 70% at 40% 55%, rgb(var(--wx-tint) / ${spec.opacity * 0.5}) 0%, transparent 70%),
                     radial-gradient(55% 65% at 68% 45%, rgb(var(--wx-tint) / ${spec.opacity * 0.4}) 0%, transparent 72%),
                     radial-gradient(70% 60% at 50% 62%, color-mix(in srgb, ${accent} ${Math.round(
                       spec.opacity * 22,
                     )}%, transparent) 0%, transparent 74%)`,
        '--wx-drift-from': `${spec.from}%`,
        '--wx-drift-to': `${spec.to}%`,
        animationDuration: `${spec.duration}s`,
        animationDelay: `${index * -1.4}s`,
      }}
    />
  )
}

/**
 * Falling particles.
 *
 * Rain is a thin streak, snow a round flake — the same element with a
 * different aspect ratio and a wider sway. Position, delay and duration are
 * derived from the index, so the scatter is stable across renders.
 */
export function Drops({ spec, accent }) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {Array.from({ length: spec.count }, (_, index) => {
        const left = scatter(index, 1) * 100
        const delay = scatter(index, 2) * 0.9
        const duration = spec.speed * (0.78 + scatter(index, 3) * 0.5)
        const drift = (scatter(index, 4) - 0.5) * 2 * spec.sway
        const depth = 0.55 + scatter(index, 5) * 0.45
        return (
          <span
            key={index}
            className="wx-intro-drop absolute block"
            style={{
              left: `${left}%`,
              top: `${-12 - scatter(index, 6) * 18}%`,
              width: spec.width * depth,
              height: spec.length * depth,
              borderRadius: spec.round ? '50%' : `${spec.width}px`,
              background: spec.round
                ? `rgb(var(--wx-tint) / ${spec.opacity * depth})`
                : `linear-gradient(to bottom, transparent, color-mix(in srgb, ${accent} 70%, transparent) 30%,
                   color-mix(in srgb, ${accent} 92%, transparent))`,
              opacity: spec.opacity * depth,
              '--wx-drop-drift': `${drift}px`,
              // Viewport units, not percent: a percentage in `translate`
              // resolves against the element's own box, so a 16px drop would
              // fall 19px and never reach the screen.
              '--wx-drop-spread': `${118 + spec.spread * 30}vh`,
              animationDuration: `${duration}s`,
              animationDelay: `${delay}s`,
            }}
          />
        )
      })}
    </div>
  )
}

/** Slow sheets of atmosphere. Fog is mostly this; rain gets one for wetness. */
export function Veils({ count, accent }) {
  return (
    <>
      {Array.from({ length: count }, (_, index) => (
        <div
          key={index}
          className="wx-intro-veil pointer-events-none absolute inset-x-[-30%]"
          style={{
            top: `${18 + index * 17}%`,
            height: `${22 + index * 6}%`,
            background: `linear-gradient(90deg, transparent, rgb(var(--wx-tint) / ${0.05 + index * 0.012}),
                         color-mix(in srgb, ${accent} 6%, transparent), transparent)`,
            animationDuration: `${16 + index * 5}s`,
            animationDelay: `${index * -3}s`,
          }}
        />
      ))}
    </>
  )
}

/** Slow floating specks. Only for calm skies, where there is air to see. */
export function Motes({ count, accent }) {
  return (
    <>
      {Array.from({ length: count }, (_, index) => {
        const size = 2 + scatter(index, 7) * 3
        return (
          <span
            key={index}
            className="wx-intro-mote pointer-events-none absolute block rounded-full"
            style={{
              left: `${8 + scatter(index, 8) * 84}%`,
              top: `${18 + scatter(index, 9) * 60}%`,
              width: size,
              height: size,
              background: `color-mix(in srgb, ${accent} 70%, transparent)`,
              animationDuration: `${5 + scatter(index, 10) * 4}s`,
              animationDelay: `${scatter(index, 11) * -5}s`,
            }}
          />
        )
      })}
    </>
  )
}

/**
 * Lightning.
 *
 * Each entry in `flashes` fires once at its own offset. Driving it from state
 * rather than a looping keyframe is what keeps it to two flashes total — a
 * CSS loop would keep firing for as long as the element lived, and a storm
 * intro that strobes is both unpleasant and unsafe.
 */
export function Lightning({ flashes }) {
  const [lit, setLit] = useState(0)

  useEffect(() => {
    const timers = flashes.map((flash) =>
      window.setTimeout(() => {
        setLit(flash.peak)
        window.setTimeout(() => setLit(0), 110)
      }, flash.at),
    )
    return () => timers.forEach(window.clearTimeout)
  }, [flashes])

  return (
    <div
      className="pointer-events-none absolute inset-0"
      style={{
        background:
          'radial-gradient(120% 80% at 50% 8%, rgb(var(--wx-tint) / 0.9) 0%, rgb(var(--wx-tint) / 0.25) 40%, transparent 72%)',
        opacity: lit,
        transition: 'opacity 90ms ease-out',
      }}
    />
  )
}
