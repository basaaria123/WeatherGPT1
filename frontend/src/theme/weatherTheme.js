/**
 * Weather-responsive theming.
 *
 * ONE normalisation step feeds everything downstream — the condition text, the
 * icon, the atmosphere and the accent colours all read from the same resolved
 * state, so the interface can never show a sun next to the word "drizzle".
 *
 *      current.weather_code + is_day
 *                  ↓
 *          normalizeCondition()          → CONDITION.*
 *                  ↓
 *          resolveTheme()                → theme token set
 *                  ↓
 *      ┌───────────┼───────────┬──────────────┐
 *   condition     icon      atmosphere      accents
 *
 * Themes stay inside the WeatherGPT palette (deep navy, sky blue, cyan, teal,
 * warm yellow) and change roughly a quarter of the surface: background
 * atmosphere, accent, and the subtle pattern behind the cards. Layout,
 * typography, card geometry and text contrast are deliberately identical across
 * every theme, so the app stays recognisable and stays readable.
 */

export const CONDITION = {
  CLEAR: 'CLEAR',
  PARTLY_CLOUDY: 'PARTLY_CLOUDY',
  CLOUDY: 'CLOUDY',
  DRIZZLE: 'DRIZZLE',
  RAIN: 'RAIN',
  HEAVY_RAIN: 'HEAVY_RAIN',
  THUNDERSTORM: 'THUNDERSTORM',
  FOG: 'FOG',
  SNOW: 'SNOW',
  UNKNOWN: 'UNKNOWN',
}

/**
 * WMO 4677 → normalised condition. Mirrors backend/app/services/wmo.py; a code
 * outside the table resolves to UNKNOWN rather than being guessed into a
 * neighbouring condition.
 */
const CODE_TO_CONDITION = {
  0: CONDITION.CLEAR,
  1: CONDITION.CLEAR,
  2: CONDITION.PARTLY_CLOUDY,
  3: CONDITION.CLOUDY,
  45: CONDITION.FOG,
  48: CONDITION.FOG,
  51: CONDITION.DRIZZLE,
  53: CONDITION.DRIZZLE,
  55: CONDITION.DRIZZLE,
  56: CONDITION.DRIZZLE,
  57: CONDITION.DRIZZLE,
  61: CONDITION.RAIN,
  63: CONDITION.RAIN,
  65: CONDITION.HEAVY_RAIN,
  66: CONDITION.RAIN,
  67: CONDITION.HEAVY_RAIN,
  71: CONDITION.SNOW,
  73: CONDITION.SNOW,
  75: CONDITION.SNOW,
  77: CONDITION.SNOW,
  80: CONDITION.RAIN,
  81: CONDITION.RAIN,
  82: CONDITION.HEAVY_RAIN,
  85: CONDITION.SNOW,
  86: CONDITION.SNOW,
  95: CONDITION.THUNDERSTORM,
  96: CONDITION.THUNDERSTORM,
  99: CONDITION.THUNDERSTORM,
}

export function normalizeCondition(weatherCode) {
  if (weatherCode === null || weatherCode === undefined) return CONDITION.UNKNOWN
  return CODE_TO_CONDITION[Number(weatherCode)] ?? CONDITION.UNKNOWN
}

/** Theme key for a normalised condition. Night and severe risk override it. */
const CONDITION_TO_THEME = {
  [CONDITION.CLEAR]: 'clear',
  [CONDITION.PARTLY_CLOUDY]: 'cloudy',
  [CONDITION.CLOUDY]: 'cloudy',
  [CONDITION.DRIZZLE]: 'rain',
  [CONDITION.RAIN]: 'rain',
  [CONDITION.HEAVY_RAIN]: 'rain',
  [CONDITION.THUNDERSTORM]: 'storm',
  [CONDITION.FOG]: 'fog',
  [CONDITION.SNOW]: 'fog',
  [CONDITION.UNKNOWN]: 'base',
}

/**
 * Token sets.
 *
 * Text tokens are identical everywhere on purpose: contrast is not something a
 * weather condition gets to negotiate. What changes is the ground the cards sit
 * on, the accent, and the atmospheric wash.
 */
export const THEMES = {
  base: {
    bg: '#050d1a', bgDeep: '#030814', raised: '#0a172b', surface: '#0e1c33',
    primary: '#22d3ee', accent: '#60a5fa', border: '#1e3050',
    atmosA: 'rgb(34 211 238 / 0.07)', atmosB: 'rgb(45 212 191 / 0.05)',
    pattern: 'none',
  },
  clear: {
    // Warm, lifted navy — bright for a dark interface without losing contrast.
    bg: '#0a1626', bgDeep: '#060f1d', raised: '#122036', surface: '#16273f',
    primary: '#f5c542', accent: '#42a5f5', border: '#2a3d59',
    atmosA: 'rgb(245 197 66 / 0.13)', atmosB: 'rgb(66 165 245 / 0.07)',
    // Soft sunlight falling from the upper left.
    pattern: 'radial-gradient(120% 80% at 12% -10%, rgb(245 197 66 / 0.10), transparent 62%)',
  },
  cloudy: {
    bg: '#0a1421', bgDeep: '#060e18', raised: '#101d2e', surface: '#152436',
    primary: '#38a3c7', accent: '#64748b', border: '#243448',
    atmosA: 'rgb(100 116 139 / 0.11)', atmosB: 'rgb(56 163 199 / 0.06)',
    pattern:
      'radial-gradient(90% 60% at 78% 8%, rgb(148 163 184 / 0.09), transparent 60%),' +
      'radial-gradient(70% 50% at 18% 24%, rgb(148 163 184 / 0.06), transparent 62%)',
  },
  rain: {
    bg: '#0b1f33', bgDeep: '#071726', raised: '#102a43', surface: '#153b56',
    primary: '#38bdf8', accent: '#22d3ee', border: '#1f4a6b',
    atmosA: 'rgb(56 189 248 / 0.12)', atmosB: 'rgb(34 211 238 / 0.07)',
    // Rain falls at an angle; the texture reads as motion without animating.
    pattern:
      'repeating-linear-gradient(72deg, rgb(56 189 248 / 0.045) 0 1px, transparent 1px 9px),' +
      'radial-gradient(100% 70% at 50% 0%, rgb(56 189 248 / 0.09), transparent 65%)',
  },
  storm: {
    bg: '#071426', bgDeep: '#040d1b', raised: '#0b1f3a', surface: '#12294a',
    primary: '#38bdf8', accent: '#fbbf24', border: '#1c3357',
    atmosA: 'rgb(37 99 235 / 0.15)', atmosB: 'rgb(251 191 36 / 0.05)',
    pattern:
      'radial-gradient(110% 70% at 50% -12%, rgb(37 99 235 / 0.16), transparent 62%),' +
      'radial-gradient(60% 40% at 80% 12%, rgb(56 189 248 / 0.07), transparent 60%)',
  },
  fog: {
    bg: '#0d1620', bgDeep: '#09111a', raised: '#141f2b', surface: '#1a2735',
    primary: '#78909c', accent: '#90a4ae', border: '#27333f',
    atmosA: 'rgb(120 144 156 / 0.13)', atmosB: 'rgb(144 164 174 / 0.08)',
    // Layered bands read as haze sitting in front of the content.
    pattern:
      'linear-gradient(0deg, rgb(144 164 174 / 0.07) 0%, transparent 28%),' +
      'linear-gradient(180deg, rgb(144 164 174 / 0.06) 0%, transparent 34%)',
  },
  night: {
    bg: '#07111f', bgDeep: '#040a14', raised: '#0e2035', surface: '#132a44',
    primary: '#60a5fa', accent: '#fbbf77', border: '#1d3350',
    atmosA: 'rgb(96 165 250 / 0.10)', atmosB: 'rgb(251 191 119 / 0.04)',
    pattern: 'radial-gradient(100% 70% at 70% -8%, rgb(96 165 250 / 0.10), transparent 62%)',
  },
}

/**
 * Resolve the theme for a set of conditions.
 *
 * Precedence is deliberate: an active storm or a Severe reading outranks the
 * time of day, because a severe night thunderstorm should look like a storm,
 * not like a calm night.
 */
// Hazards whose *sky* actually looks like a storm. Extreme heat and strong
// wind can both be Severe under a clear sky, and painting those as a
// thunderstorm would contradict the condition shown next to them.
const STORMY_HAZARDS = new Set(['Lightning/Storm', 'Flood Risk', 'Heavy Rainfall'])

export function resolveTheme({ weatherCode, isDay = true, riskLevel, hazard } = {}) {
  const condition = normalizeCondition(weatherCode)

  if (hazard === 'Lightning/Storm' || condition === CONDITION.THUNDERSTORM) return 'storm'
  // Severity alone does not repaint the sky — only a severe hazard that would
  // actually darken it. Severity is carried by the risk pill and the alerts.
  if (riskLevel === 'Severe' && STORMY_HAZARDS.has(hazard)) return 'storm'

  const byCondition = CONDITION_TO_THEME[condition] ?? 'base'
  // Night only reclaims the calm themes; rain at night still looks like rain.
  if (isDay === false && (byCondition === 'clear' || byCondition === 'cloudy' || byCondition === 'base')) {
    return 'night'
  }
  return byCondition
}

const VAR_MAP = {
  '--wx-bg': 'bg',
  '--wx-bg-deep': 'bgDeep',
  '--wx-raised': 'raised',
  '--wx-surface': 'surface',
  '--wx-primary': 'primary',
  '--wx-accent': 'accent',
  '--wx-border': 'border',
  '--wx-atmos-a': 'atmosA',
  '--wx-atmos-b': 'atmosB',
  '--wx-pattern': 'pattern',
}

/**
 * Write the theme onto the document root. Applied in one place so no component
 * hardcodes a weather colour, and so the CSS transition runs once for the whole
 * page rather than per component.
 */
export function applyTheme(themeKey) {
  const theme = THEMES[themeKey] ?? THEMES.base
  const root = document.documentElement
  Object.entries(VAR_MAP).forEach(([cssVar, key]) => {
    root.style.setProperty(cssVar, theme[key])
  })
  root.dataset.weatherTheme = themeKey
}

export const THEME_KEYS = Object.keys(THEMES)

/**
 * 3D background scene for a normalised condition.
 *
 * Shares the same normalisation as the text, icon and theme, so the scene
 * behind the dashboard can never disagree with the words in front of it.
 */
const CONDITION_TO_SCENE = {
  [CONDITION.CLEAR]: 'clear',
  [CONDITION.PARTLY_CLOUDY]: 'cloudy',
  [CONDITION.CLOUDY]: 'cloudy',
  [CONDITION.DRIZZLE]: 'rain',
  [CONDITION.RAIN]: 'rain',
  [CONDITION.HEAVY_RAIN]: 'rain',
  [CONDITION.THUNDERSTORM]: 'storm',
  [CONDITION.FOG]: 'fog',
  [CONDITION.SNOW]: 'snow',
  [CONDITION.UNKNOWN]: 'clear',
}

export function sceneForCondition({ weatherCode, riskLevel, hazard } = {}) {
  if (hazard === 'Extreme Heat') return 'heat'
  if (hazard === 'Lightning/Storm') return 'storm'
  if (riskLevel === 'Severe' && STORMY_HAZARDS.has(hazard)) return 'storm'
  return CONDITION_TO_SCENE[normalizeCondition(weatherCode)] ?? 'clear'
}
