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
    scheme: 'dark',
    scrim: '3 8 20', overlay: 'rgb(2 6 14 / 0.72)',
    bg: '#050d1a', bgDeep: '#030814', raised: '#0a172b', surface: '#0e1c33',
    primary: '#22d3ee', accent: '#60a5fa', border: '#1e3050',
    tint: '255 255 255',
    ink: '#f1f5f9', inkSoft: '#cbd5e1', muted: '#94a3b8', faint: '#64748b',
    safe: '#34d399', caution: '#fbbf24', warning: '#fb923c', danger: '#f43f5e',
    vignette: 'radial-gradient(115% 78% at 50% 0%, transparent 30%, rgb(3 8 20 / 0.55) 78%, rgb(3 8 20 / 0.85) 100%)',
    shadowGlass: '0 6px 20px rgb(2 8 20 / 0.38)',
    shadowLift: '0 10px 30px rgb(2 8 20 / 0.46)',
    atmosA: 'rgb(34 211 238 / 0.07)', atmosB: 'rgb(45 212 191 / 0.05)',
    pattern: 'none',
  },

  // --- Light themes ------------------------------------------------------
  // Bright conditions get a bright interface. Text and severity colours are
  // darkened to keep contrast; yellow never appears as text on white.
  clear: {
    scheme: 'light',
    scrim: '234 247 255', overlay: 'rgb(23 45 68 / 0.42)',
    bg: '#f8fbff', bgDeep: '#eaf7ff', raised: '#ffffff', surface: '#ffffff',
    primary: '#e0952a', accent: '#2f7fc4', border: '#cfe3f5',
    tint: '16 42 67',
    ink: '#102a43', inkSoft: '#24405c', muted: '#4a6785', faint: '#71889f',
    safe: '#0f7f57', caution: '#a16207', warning: '#c2410c', danger: '#be123c',
    vignette: 'radial-gradient(115% 78% at 50% 0%, transparent 34%, rgb(214 233 249 / 0.42) 80%, rgb(200 226 247 / 0.62) 100%)',
    shadowGlass: '0 4px 16px rgb(28 63 99 / 0.10)',
    shadowLift: '0 10px 28px rgb(28 63 99 / 0.14)',
    atmosA: 'rgb(245 185 66 / 0.16)', atmosB: 'rgb(66 165 245 / 0.10)',
    pattern: 'radial-gradient(120% 80% at 12% -10%, rgb(245 185 66 / 0.16), transparent 62%)',
  },
  cloudy: {
    scheme: 'light',
    scrim: '226 232 240', overlay: 'rgb(23 43 58 / 0.42)',
    bg: '#eef3f7', bgDeep: '#e2e8f0', raised: '#ffffff', surface: '#ffffff',
    primary: '#2f7f9c', accent: '#546b82', border: '#cbd8e3',
    tint: '23 43 58',
    ink: '#172b3a', inkSoft: '#2c4356', muted: '#4f6579', faint: '#78899b',
    safe: '#0f7f57', caution: '#a16207', warning: '#c2410c', danger: '#be123c',
    vignette: 'radial-gradient(115% 78% at 50% 0%, transparent 34%, rgb(203 216 227 / 0.45) 80%, rgb(190 205 218 / 0.65) 100%)',
    shadowGlass: '0 4px 16px rgb(30 50 68 / 0.10)',
    shadowLift: '0 10px 28px rgb(30 50 68 / 0.14)',
    atmosA: 'rgb(100 116 139 / 0.14)', atmosB: 'rgb(56 163 199 / 0.08)',
    pattern:
      'radial-gradient(90% 60% at 78% 8%, rgb(120 145 170 / 0.14), transparent 60%),' +
      'radial-gradient(70% 50% at 18% 24%, rgb(120 145 170 / 0.10), transparent 62%)',
  },
  fog: {
    scheme: 'light',
    scrim: '220 229 234', overlay: 'rgb(38 50 56 / 0.42)',
    bg: '#e9eef2', bgDeep: '#dce5ea', raised: '#ffffff', surface: '#ffffff',
    primary: '#4d6b7a', accent: '#657f8c', border: '#c7d3da',
    tint: '38 50 56',
    ink: '#263238', inkSoft: '#3b4a52', muted: '#5b6d76', faint: '#84939b',
    safe: '#0f7f57', caution: '#a16207', warning: '#c2410c', danger: '#be123c',
    vignette: 'radial-gradient(115% 78% at 50% 0%, transparent 30%, rgb(214 224 230 / 0.55) 74%, rgb(202 214 222 / 0.75) 100%)',
    shadowGlass: '0 4px 16px rgb(38 50 56 / 0.09)',
    shadowLift: '0 10px 28px rgb(38 50 56 / 0.13)',
    atmosA: 'rgb(120 144 156 / 0.16)', atmosB: 'rgb(144 164 174 / 0.10)',
    pattern:
      'linear-gradient(0deg, rgb(120 144 156 / 0.12) 0%, transparent 28%),' +
      'linear-gradient(180deg, rgb(120 144 156 / 0.10) 0%, transparent 34%)',
  },

  // --- Dark themes -------------------------------------------------------
  rain: {
    scheme: 'dark',
    scrim: '7 23 38', overlay: 'rgb(3 12 22 / 0.72)',
    bg: '#0b1f33', bgDeep: '#071726', raised: '#102a43', surface: '#153b56',
    primary: '#38bdf8', accent: '#22d3ee', border: '#1f4a6b',
    tint: '255 255 255',
    ink: '#f8fafc', inkSoft: '#dce7f2', muted: '#b8c7d9', faint: '#8aa0b8',
    safe: '#34d399', caution: '#fbbf24', warning: '#fb923c', danger: '#fb7185',
    vignette: 'radial-gradient(115% 78% at 50% 0%, transparent 30%, rgb(4 14 26 / 0.52) 78%, rgb(4 14 26 / 0.82) 100%)',
    shadowGlass: '0 6px 20px rgb(2 12 24 / 0.40)',
    shadowLift: '0 10px 30px rgb(2 12 24 / 0.50)',
    atmosA: 'rgb(56 189 248 / 0.12)', atmosB: 'rgb(34 211 238 / 0.07)',
    pattern:
      'repeating-linear-gradient(72deg, rgb(56 189 248 / 0.05) 0 1px, transparent 1px 9px),' +
      'radial-gradient(100% 70% at 50% 0%, rgb(56 189 248 / 0.10), transparent 65%)',
  },
  storm: {
    scheme: 'dark',
    scrim: '4 13 27', overlay: 'rgb(2 8 18 / 0.75)',
    bg: '#071426', bgDeep: '#040d1b', raised: '#0b1f3a', surface: '#12294a',
    primary: '#38bdf8', accent: '#fbbf24', border: '#1c3357',
    tint: '255 255 255',
    ink: '#f8fafc', inkSoft: '#dbe6f5', muted: '#a8bcd6', faint: '#7c93b0',
    safe: '#34d399', caution: '#fbbf24', warning: '#fb923c', danger: '#fb7185',
    vignette: 'radial-gradient(115% 78% at 50% 0%, transparent 28%, rgb(2 8 18 / 0.58) 76%, rgb(2 8 18 / 0.88) 100%)',
    shadowGlass: '0 6px 20px rgb(1 6 16 / 0.46)',
    shadowLift: '0 10px 30px rgb(1 6 16 / 0.56)',
    atmosA: 'rgb(37 99 235 / 0.16)', atmosB: 'rgb(251 191 36 / 0.06)',
    pattern:
      'radial-gradient(110% 70% at 50% -12%, rgb(37 99 235 / 0.18), transparent 62%),' +
      'radial-gradient(60% 40% at 80% 12%, rgb(56 189 248 / 0.08), transparent 60%)',
  },
  night: {
    scheme: 'dark',
    scrim: '4 10 20', overlay: 'rgb(2 7 15 / 0.74)',
    bg: '#07111f', bgDeep: '#040a14', raised: '#0e2035', surface: '#132a44',
    primary: '#60a5fa', accent: '#fbbf77', border: '#1d3350',
    tint: '255 255 255',
    ink: '#f8fafc', inkSoft: '#dce6f3', muted: '#a9bbd2', faint: '#7d91ac',
    safe: '#34d399', caution: '#fbbf24', warning: '#fb923c', danger: '#fb7185',
    vignette: 'radial-gradient(115% 78% at 50% 0%, transparent 30%, rgb(2 7 15 / 0.55) 78%, rgb(2 7 15 / 0.85) 100%)',
    shadowGlass: '0 6px 20px rgb(1 5 12 / 0.44)',
    shadowLift: '0 10px 30px rgb(1 5 12 / 0.54)',
    atmosA: 'rgb(96 165 250 / 0.11)', atmosB: 'rgb(251 191 119 / 0.05)',
    pattern: 'radial-gradient(100% 70% at 70% -8%, rgb(96 165 250 / 0.11), transparent 62%)',
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
  '--wx-tint': 'tint',
  '--wx-ink': 'ink',
  '--wx-vignette': 'vignette',
  '--wx-scrim': 'scrim',
  '--wx-overlay': 'overlay',
  // The app's semantic tokens are overridden too. Because every component
  // already styles through `text-ink` / `bg-primary` / severity colours rather
  // than hex values, re-pointing these re-themes the whole interface — which is
  // what makes a light theme possible without touching components.
  '--color-bg': 'bg',
  '--color-bg-deep': 'bgDeep',
  '--color-bg-raised': 'raised',
  '--color-surface': 'surface',
  '--color-border': 'border',
  '--color-primary': 'primary',
  '--color-accent': 'accent',
  '--color-ink': 'ink',
  '--color-ink-soft': 'inkSoft',
  '--color-muted': 'muted',
  '--color-faint': 'faint',
  '--color-safe': 'safe',
  '--color-caution': 'caution',
  '--color-warning': 'warning',
  '--color-danger': 'danger',
  '--shadow-glass': 'shadowGlass',
  '--shadow-lift': 'shadowLift',
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
    if (theme[key] !== undefined) root.style.setProperty(cssVar, theme[key])
  })
  root.dataset.weatherTheme = themeKey
  // Drives the browser's own controls, scrollbars and caret colour.
  root.style.colorScheme = theme.scheme ?? 'dark'
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
