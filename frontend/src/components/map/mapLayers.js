/**
 * The four map layers, and what each honestly knows.
 *
 * A layer is a pure description: which field it reads, how to colour a value,
 * what its legend says, and — the part that matters most — whether the field
 * exists in the forward hourly series at all.
 *
 * `hourly: false` is not a bug to work around. The provider's hourly block
 * carries temperature, precipitation and wind but no cloud cover, so the cloud
 * layer can only speak for the present hour. Saying that plainly is the whole
 * difference between a weather map and a decorative one.
 */

// Stops are the app's own severity palette, so a heavy-rain marker is the same
// colour as a heavy-rain risk pill elsewhere on the page.
const SAFE = 'var(--color-safe)'
const CAUTION = 'var(--color-caution)'
const WARN = 'var(--color-warning)'
const DANGER = 'var(--color-danger)'
const COOL = 'var(--color-accent)'
const CALM = 'var(--color-primary)'

/** Pick a stop by threshold. Values below the first stop take the first colour. */
function rampOf(stops) {
  return (value) => {
    let chosen = stops[0]
    for (const stop of stops) if (value >= stop.at) chosen = stop
    return chosen.color
  }
}

export const LAYERS = {
  rain: {
    id: 'rain',
    icon: '🌧️',
    labelKey: 'layerRain',
    // Probability is the field a reader actually reasons about, and it exists
    // for every hour as well as for now.
    field: 'precipitation_probability_pct',
    hourlyField: 'precipitation_probability_pct',
    hourly: true,
    unit: '%',
    decimals: 0,
    legendKeys: ['legendLow', 'legendModerate', 'legendHigh'],
    ramp: rampOf([
      { at: 0, color: SAFE },
      { at: 30, color: CAUTION },
      { at: 60, color: WARN },
      { at: 80, color: DANGER },
    ]),
    // A marker's size carries the value too, so the reading survives greyscale
    // and colour blindness.
    scale: (value) => Math.min(1, Math.max(0, value / 100)),
  },

  wind: {
    id: 'wind',
    icon: '🌬️',
    labelKey: 'layerWind',
    field: 'wind_speed_kmh',
    hourlyField: 'wind_speed_kmh',
    hourly: true,
    unit: ' km/h',
    decimals: 0,
    legendKeys: ['legendLower', 'legendHigher'],
    ramp: rampOf([
      { at: 0, color: CALM },
      { at: 20, color: CAUTION },
      { at: 35, color: WARN },
      { at: 50, color: DANGER },
    ]),
    scale: (value) => Math.min(1, Math.max(0, value / 60)),
    // Direction is a present-moment reading only; the hourly series has none,
    // so the arrow is drawn for "now" and dropped once the reader scrubs on.
    bearingField: 'wind_direction_deg',
  },

  temperature: {
    id: 'temperature',
    icon: '🌡️',
    labelKey: 'layerTemperature',
    field: 'temperature_c',
    hourlyField: 'temperature_c',
    hourly: true,
    unit: '°',
    decimals: 0,
    legendKeys: ['legendCool', 'legendModerate', 'legendHot'],
    ramp: rampOf([
      { at: -20, color: COOL },
      { at: 22, color: CALM },
      { at: 30, color: CAUTION },
      { at: 36, color: WARN },
      { at: 42, color: DANGER },
    ]),
    scale: (value) => Math.min(1, Math.max(0, (value - 5) / 40)),
  },

  clouds: {
    id: 'clouds',
    icon: '☁️',
    labelKey: 'layerClouds',
    field: 'cloud_cover_pct',
    hourlyField: null,
    // The honest flag. Everything downstream reads this rather than guessing.
    hourly: false,
    unit: '%',
    decimals: 0,
    legendKeys: ['legendClear', 'legendOvercast'],
    ramp: rampOf([
      { at: 0, color: CALM },
      { at: 40, color: 'var(--color-muted)' },
      { at: 75, color: 'var(--color-ink-soft)' },
    ]),
    scale: (value) => Math.min(1, Math.max(0, value / 100)),
  },
}

export const LAYER_ORDER = ['rain', 'wind', 'temperature', 'clouds']

/**
 * The value a layer should show for one place at one step.
 *
 * `step === 0` is the present and reads the measured current value. A later
 * step reads that place's own forecast hour — never an interpolation between
 * places, and never a value carried forward from the present and presented as
 * a forecast. A layer with no hourly field returns `null` beyond the present,
 * which is what makes the "current observation only" notice appear.
 */
export function valueAt(entry, layer, step) {
  if (!entry) return null
  if (step === 0) {
    const now = entry[layer.field]
    return typeof now === 'number' ? now : null
  }
  if (!layer.hourly || !layer.hourlyField) return null
  const hour = entry.hours?.[step]
  const value = hour?.[layer.hourlyField]
  return typeof value === 'number' ? value : null
}

/** How many steps every place on the map can actually support. */
export function stepsAvailable(entries) {
  if (!entries?.length) return 1
  const shortest = entries.reduce(
    (least, entry) => Math.min(least, (entry.hours?.length ?? 0)),
    Number.POSITIVE_INFINITY,
  )
  return Number.isFinite(shortest) ? Math.max(1, shortest) : 1
}
