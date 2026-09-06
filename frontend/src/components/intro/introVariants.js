import { CONDITION } from '../../theme/weatherTheme'

/**
 * What each weather condition looks like for the two seconds it introduces
 * itself.
 *
 * This module deliberately does no weather interpretation. It is keyed by the
 * `CONDITION.*` value `normalizeCondition()` already produced from the same
 * `weather_code` the hero card, the glyph and the theme read, so the intro
 * cannot disagree with the dashboard behind it — there is one reading of the
 * sky, and this is a costume for it, not a second opinion.
 *
 * A recipe is data, not markup:
 *
 *   sun      a warm disc, and how strongly it burns through
 *   clouds   how many soft banks drift across, and how dark they are
 *   drops    falling particles — their shape, count, speed and drift
 *   veils    slow atmospheric sheets, for fog and mist
 *   flashes  lightning, as explicit timings rather than a loop
 *   accent   the colour the wash, drops and glow are tinted with
 *
 * Counts are the desktop figures; `scaleForViewport` thins them on a phone,
 * where the same density would cost more and read as noise.
 */

/**
 * The intro's two colours, fixed rather than borrowed.
 *
 * `--color-accent` is the obvious candidate and the wrong one: it is the
 * theme's *warm* slot and legitimately becomes amber under the storm and night
 * themes, which turns rain into a shower of sparks. These are the same sky
 * blue and warm yellow from the app's own palette, chosen once so a condition
 * always looks like itself whatever ground it lands on.
 */
const WATER = '#60a5fa'
const SUN = '#fbbf24'

export const VARIANTS = {
  [CONDITION.CLEAR]: {
    accent: SUN,
    wash: 0.088,
    sun: { size: 230, glow: 0.55 },
    clouds: [],
    drops: null,
    veils: 0,
    flashes: [],
    motes: 12,
  },

  [CONDITION.PARTLY_CLOUDY]: {
    accent: SUN,
    wash: 0.072,
    sun: { size: 190, glow: 0.4 },
    // One bank crosses the sun; the second sits lower and drifts the other way.
    clouds: [
      { top: 14, size: 1.05, opacity: 0.25, duration: 9, from: -18, to: 26 },
      { top: 28, size: 0.8, opacity: 0.16, duration: 12, from: 34, to: -14 },
    ],
    drops: null,
    veils: 0,
    motes: 8,
    flashes: [],
  },

  [CONDITION.CLOUDY]: {
    accent: WATER,
    wash: 0.066,
    sun: null,
    clouds: [
      { top: 10, size: 1.25, opacity: 0.28, duration: 11, from: -22, to: 20 },
      { top: 26, size: 1, opacity: 0.21, duration: 14, from: 30, to: -18 },
      { top: 32, size: 0.85, opacity: 0.14, duration: 17, from: -10, to: 24 },
    ],
    drops: null,
    veils: 1,
    motes: 0,
    flashes: [],
  },

  [CONDITION.DRIZZLE]: {
    accent: WATER,
    wash: 0.083,
    sun: null,
    clouds: [
      { top: 8, size: 1.2, opacity: 0.25, duration: 12, from: -18, to: 18 },
      { top: 24, size: 0.95, opacity: 0.17, duration: 15, from: 26, to: -12 },
    ],
    // Fine and slow: drizzle is felt more than it is seen.
    drops: { count: 34, length: 9, width: 1, speed: 1.5, spread: 0.5, sway: 4, opacity: 0.45 },
    veils: 2,
    motes: 0,
    flashes: [],
  },

  [CONDITION.RAIN]: {
    accent: WATER,
    wash: 0.094,
    sun: null,
    clouds: [
      { top: 6, size: 1.3, opacity: 0.29, duration: 10, from: -20, to: 18 },
      { top: 22, size: 1, opacity: 0.20, duration: 13, from: 28, to: -14 },
    ],
    drops: { count: 42, length: 20, width: 1.4, speed: 0.95, spread: 0.35, sway: 6, opacity: 0.6 },
    veils: 1,
    motes: 0,
    flashes: [],
  },

  [CONDITION.HEAVY_RAIN]: {
    accent: WATER,
    wash: 0.121,
    sun: null,
    clouds: [
      { top: 4, size: 1.45, opacity: 0.36, duration: 8, from: -24, to: 20 },
      { top: 18, size: 1.15, opacity: 0.28, duration: 11, from: 30, to: -16 },
      { top: 32, size: 0.9, opacity: 0.19, duration: 14, from: -12, to: 26 },
    ],
    drops: { count: 64, length: 30, width: 1.6, speed: 0.62, spread: 0.22, sway: 9, opacity: 0.72 },
    veils: 1,
    motes: 0,
    flashes: [],
  },

  [CONDITION.THUNDERSTORM]: {
    accent: WATER,
    wash: 0.143,
    sun: null,
    clouds: [
      { top: 3, size: 1.5, opacity: 0.40, duration: 9, from: -26, to: 18 },
      { top: 17, size: 1.2, opacity: 0.30, duration: 12, from: 32, to: -18 },
      { top: 29, size: 0.95, opacity: 0.21, duration: 15, from: -14, to: 24 },
    ],
    drops: { count: 52, length: 26, width: 1.5, speed: 0.7, spread: 0.26, sway: 10, opacity: 0.66 },
    veils: 1,
    motes: 0,
    // Two brief, low-amplitude flashes. Never a loop, never a strobe: seizure
    // safety guidance puts the ceiling at three flashes a second and this is
    // well under one, with a soft peak rather than a hard white frame.
    flashes: [
      { at: 520, peak: 0.3 },
      { at: 1080, peak: 0.2 },
    ],
  },

  [CONDITION.FOG]: {
    accent: WATER,
    wash: 0.110,
    sun: null,
    clouds: [{ top: 22, size: 1.6, opacity: 0.15, duration: 20, from: -20, to: 16 }],
    drops: null,
    veils: 4,
    motes: 0,
    flashes: [],
  },

  [CONDITION.SNOW]: {
    accent: WATER,
    wash: 0.077,
    sun: null,
    clouds: [
      { top: 8, size: 1.2, opacity: 0.23, duration: 14, from: -16, to: 18 },
      { top: 24, size: 0.9, opacity: 0.15, duration: 18, from: 26, to: -12 },
    ],
    // Round, slow and wandering rather than falling in a line.
    drops: { count: 38, length: 4, width: 4, speed: 2.6, spread: 0.9, sway: 26, opacity: 0.7, round: true },
    veils: 1,
    motes: 0,
    flashes: [],
  },

  /**
   * No reading of the sky, so nothing is drawn of it.
   *
   * A code the app cannot map must not be dressed as the nearest weather it
   * resembles — inventing sun or rain here would be the one failure mode worse
   * than showing nothing. What is left is a plain atmospheric wipe that claims
   * no condition at all.
   */
  [CONDITION.UNKNOWN]: {
    accent: WATER,
    wash: 0.055,
    sun: null,
    clouds: [],
    drops: null,
    veils: 1,
    motes: 0,
    flashes: [],
  },
}

export function variantFor(condition) {
  return VARIANTS[condition] ?? VARIANTS[CONDITION.UNKNOWN]
}

/**
 * Thin the particle counts on small screens.
 *
 * A phone has a third of the area and less budget to paint it with, so the
 * desktop density would cost more and read as static rather than weather.
 */
export function scaleForViewport(variant, width) {
  const factor = width < 480 ? 0.5 : width < 900 ? 0.75 : 1
  if (factor === 1) return variant
  return {
    ...variant,
    motes: Math.round(variant.motes * factor),
    clouds: variant.clouds.slice(0, Math.max(1, Math.round(variant.clouds.length * factor))),
    drops: variant.drops ? { ...variant.drops, count: Math.round(variant.drops.count * factor) } : null,
    veils: Math.max(variant.veils > 0 ? 1 : 0, Math.round(variant.veils * factor)),
  }
}

/**
 * Deterministic placement.
 *
 * `Math.random()` would give a different sky on every render and make the
 * animation impossible to screenshot or reason about. This is a plain hash of
 * the particle's index, which looks scattered and is the same scatter twice.
 */
export function scatter(index, salt = 0) {
  const value = Math.sin((index + 1) * 12.9898 + salt * 78.233) * 43758.5453
  return value - Math.floor(value)
}

/**
 * The same weather, at the size of a card.
 *
 * The tap-the-icon burst plays inside the conditions card rather than over the
 * whole screen, so it wants the same sky with fewer of everything and no
 * full-bleed wash. Deriving it from the intro's own recipe is the point: there
 * is one description of what drizzle looks like, and both surfaces render it.
 */
export function scaleForBurst(variant) {
  return {
    ...variant,
    wash: 0,
    // One bank is atmosphere; three inside a card is a smudge.
    clouds: variant.clouds.slice(0, 1).map((cloud) => ({ ...cloud, top: 2, size: cloud.size * 0.55 })),
    veils: Math.min(variant.veils, 1),
    motes: Math.round(variant.motes * 0.6),
    drops: variant.drops ? { ...variant.drops, count: Math.round(variant.drops.count * 0.45) } : null,
    sun: variant.sun ? { ...variant.sun, size: Math.round(variant.sun.size * 0.55), glow: variant.sun.glow } : null,
    // One flash, early, so it lands inside the shorter window.
    flashes: variant.flashes.slice(0, 1).map((flash) => ({ ...flash, at: 260 })),
  }
}
