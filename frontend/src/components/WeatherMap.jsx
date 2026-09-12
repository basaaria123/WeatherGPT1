import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { CircleMarker, MapContainer, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { levelLabel, t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { EmptyState, Panel, Skeleton } from './ui/Primitives'
import TileStatus from './map/TileStatus'
import { LAYERS, LAYER_ORDER, stepsAvailable, valueAt } from './map/mapLayers'

/**
 * The interactive weather map.
 *
 * Every mark on it is a measured reading at a real coordinate. The markers are
 * the watched locations the risk map already fetches, now carrying the current
 * values and the forward hours that were fetched to score them — so this panel
 * makes no request of its own and adds no upstream call.
 *
 * What this is not: radar. Nothing here interpolates a field between the points
 * it has, animates precipitation across the country, or claims rain is moving
 * toward the reader. Playing the forecast steps every location through its own
 * hourly series, which is a claim the data supports; a smooth sweep across the
 * map would not be.
 *
 * The cloud layer has no hourly series behind it — the provider's hourly block
 * carries no cloud cover — so scrubbing past the present hour says so instead
 * of holding the current value up as a forecast.
 */

// Slow enough to read each step. Doubled again under reduced motion, where the
// playback becomes a series of states rather than a sweep.
const STEP_MS = 1100
const DEFAULT_ZOOM = 6
// Matches the risk map's own country view, for when no place has been chosen.
const INDIA_CENTER = [22.6, 79.5]
const INDIA_ZOOM = 4

const TILE_URL = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png'
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'

const clock = (stamp) => String(stamp ?? '').split('T')[1]?.slice(0, 5) ?? ''

/** Keeps the map on the selected place, and gives the recentre button a target. */
function Recenter({ center, zoom, token }) {
  const map = useMap()
  useEffect(() => {
    if (center) map.flyTo(center, zoom, { duration: 0.8 })
  }, [center?.[0], center?.[1], zoom, token, map]) // eslint-disable-line react-hooks/exhaustive-deps
  return null
}

export default function WeatherMap({ data, hours, insights, loading, error, tall = false, onAsk }) {
  const language = useStore((s) => s.language)
  const location = useStore((s) => s.location)
  const reduced = useReducedMotion()

  const [layerId, setLayerId] = useState('rain')
  const [step, setStep] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [recenterToken, setRecenterToken] = useState(0)
  const [mounted, setMounted] = useState(false)

  const layer = LAYERS[layerId]
  const entries = useMemo(() => data?.locations ?? [], [data])
  // The playback can only be as long as the shortest series on the map: a step
  // some markers cannot answer for is a step that would show stale colour.
  const steps = useMemo(() => stepsAvailable(entries), [entries])

  // Leaflet needs a sized container; mounting after paint avoids a 0-height map.
  useEffect(() => {
    const timer = window.setTimeout(() => setMounted(true), 60)
    return () => window.clearTimeout(timer)
  }, [])

  // A shorter series after a location change must not leave the slider past
  // the end of it.
  useEffect(() => { setStep((current) => Math.min(current, steps - 1)) }, [steps])

  // Playback. It stops at the end rather than looping, because a loop turns a
  // forecast into an animation nobody reads.
  useEffect(() => {
    if (!playing) return undefined
    if (step >= steps - 1) { setPlaying(false); return undefined }
    const timer = window.setTimeout(() => setStep((n) => n + 1), reduced ? STEP_MS * 2 : STEP_MS)
    return () => window.clearTimeout(timer)
  }, [playing, step, steps, reduced])

  // A layer with no forward series cannot be played past the present.
  useEffect(() => {
    if (!layer.hourly && step > 0) { setPlaying(false); setStep(0) }
  }, [layer.hourly, step])

  // The selected place is the anchor: it is what the timeline and the reading
  // below the map are about.
  const here = useMemo(
    () => entries.find((entry) => entry.location === location?.name) ?? null,
    [entries, location?.name],
  )

  /*
   * Where to point the map.
   *
   * The stored location only carries coordinates once it has been chosen
   * through the search dialog — the default is a name and a state, nothing
   * more. So the fallback walks to the gazetteer entry the map itself is
   * plotting, and finally to the country view the risk map already uses. All
   * three are real coordinates; none of them is a guess.
   */
  const center = useMemo(() => {
    if (typeof location?.latitude === 'number' && typeof location?.longitude === 'number') {
      return [location.latitude, location.longitude]
    }
    if (here) return [here.latitude, here.longitude]
    return INDIA_CENTER
  }, [location?.latitude, location?.longitude, here])

  // Zoomed to the region when we know where the reader is; the country when we
  // are only showing the watched set.
  const zoom = here || typeof location?.latitude === 'number' ? DEFAULT_ZOOM : INDIA_ZOOM

  const selectedHour = hours?.[step] ?? null
  const stepLabel = step === 0 ? t(language, 'mapNow') : clock(selectedHour?.time ?? here?.hours?.[step]?.time)
  const insight = insights?.[step] ?? insights?.[0] ?? ''

  const play = useCallback(() => {
    if (step >= steps - 1) setStep(0)
    setPlaying((value) => !value)
  }, [step, steps])

  // On its own page the map gets the room the dashboard could not spare.
  const mapHeight = tall ? 'min(68vh, 40rem)' : '20rem'

  if (loading && !entries.length) {
    return (
      <Panel title={t(language, 'weatherMap')}>
        <Skeleton className="h-[22rem] w-full" />
      </Panel>
    )
  }
  if (error && !entries.length) {
    // The map fails on its own; the dashboard around it is untouched.
    return (
      <Panel title={t(language, 'weatherMap')}>
        <EmptyState icon="!" message={error} />
      </Panel>
    )
  }
  if (!entries.length) return null

  const canPlay = layer.hourly && steps > 1

  return (
    <Panel
      id="weather-map"
      title={t(language, 'weatherMap')}
      action={
        <span className="flex shrink-0 items-center gap-1.5 text-[11px] tabular-nums text-muted">
          <span aria-hidden="true">🕒</span>
          <span>{stepLabel}</span>
        </span>
      }
    >
      {/* --- Layers ------------------------------------------------------- */}
      <div className="scroll-x -mx-1 mb-2.5 flex min-w-0 gap-1.5 px-1 pb-1" role="group" aria-label={t(language, 'mapLayers')}>
        {LAYER_ORDER.map((id) => {
          const option = LAYERS[id]
          const active = id === layerId
          return (
            <button
              key={id}
              type="button"
              onClick={() => setLayerId(id)}
              aria-pressed={active}
              className={`flex shrink-0 items-center gap-1.5 rounded-[var(--radius-pill)] border px-2.5 py-1.5 text-[11px]
                          font-medium transition ${
                            active
                              ? 'border-primary/60 bg-primary/15 text-primary'
                              : 'border-[rgb(var(--wx-tint)/0.10)] bg-[rgb(var(--wx-tint)/0.04)] text-muted hover:border-[rgb(var(--wx-tint)/0.25)]'
                          }`}
            >
              <span aria-hidden="true">{option.icon}</span>
              <span>{t(language, option.labelKey)}</span>
            </button>
          )
        })}
      </div>

      {/* --- Map ---------------------------------------------------------- */}
      <div className="relative min-w-0 overflow-hidden rounded-[var(--radius-card)] border border-[rgb(var(--wx-tint)/0.08)]">
        {mounted ? (
          <MapContainer
            center={center}
            zoom={zoom}
            scrollWheelZoom={false}
            style={{ height: mapHeight, width: '100%', background: 'var(--wx-bg-deep)' }}
            aria-label={t(language, 'weatherMap')}
          >
            <TileStatus url={TILE_URL} attribution={TILE_ATTRIBUTION} />
            <Recenter center={center} zoom={zoom} token={recenterToken} />
            {entries.map((entry) => (
              <LayerMarker
                key={entry.location}
                entry={entry}
                layer={layer}
                step={step}
                language={language}
                isHere={entry.location === location?.name}
                onAsk={onAsk}
              />
            ))}
          </MapContainer>
        ) : (
          <Skeleton className="h-[20rem] w-full" />
        )}

        <button
          type="button"
          onClick={() => setRecenterToken((n) => n + 1)}
          aria-label={t(language, 'mapRecenter')}
          title={t(language, 'mapRecenter')}
          className="glass absolute right-2.5 top-2.5 z-[500] grid h-8 w-8 place-items-center rounded-full
                     bg-[rgb(var(--wx-scrim)/0.85)] text-sm text-ink transition hover:text-primary"
        >
          <span aria-hidden="true">◎</span>
        </button>
      </div>

      {/* --- Legend, and what this layer can and cannot say --------------- */}
      <div className="mt-2.5 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <Legend layer={layer} language={language} />
        <p data-map-note className="text-[10.5px] leading-relaxed text-faint">
          {!layer.hourly && step === 0
            ? t(language, 'mapCurrentOnly')
            : t(language, 'mapObservationNote')}
        </p>
      </div>

      {/* --- Playback and timeline ---------------------------------------- */}
      {steps > 1 && (
        <div className="mt-3 border-t border-[rgb(var(--wx-tint)/0.07)] pt-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <button
              type="button"
              onClick={play}
              disabled={!canPlay}
              data-map-play
              aria-label={playing ? t(language, 'mapPause') : t(language, 'mapPlay')}
              className="flex shrink-0 items-center gap-1.5 rounded-[var(--radius-pill)] border border-primary/40
                         bg-primary/10 px-3 py-1.5 text-[11px] font-medium text-primary transition
                         hover:bg-primary/20 disabled:opacity-40"
            >
              <span aria-hidden="true">{playing ? '❚❚' : '▶'}</span>
              <span>{playing ? t(language, 'mapPause') : t(language, 'mapPlay')}</span>
            </button>

            <input
              type="range"
              min={0}
              max={steps - 1}
              step={1}
              value={step}
              disabled={!layer.hourly}
              onChange={(event) => { setPlaying(false); setStep(Number(event.target.value)) }}
              aria-label={t(language, 'mapTime')}
              aria-valuetext={stepLabel}
              className="wx-range min-w-0 flex-1 disabled:opacity-40"
            />
          </div>

          {/* The steps as labels, so the slider position has meaning without
              having to be dragged. */}
          <div className="scroll-x mt-2 flex min-w-0 gap-1 pb-1">
            {Array.from({ length: steps }, (_, index) => {
              const hour = hours?.[index] ?? here?.hours?.[index]
              const active = index === step
              return (
                <button
                  key={index}
                  type="button"
                  onClick={() => { setPlaying(false); setStep(index) }}
                  disabled={!layer.hourly && index > 0}
                  /* Tall enough to hit with a thumb: at `py-1` these came out
                     24px, which is under any touch-target guidance. */
                  className={`min-h-[34px] shrink-0 rounded-md px-2.5 text-[10.5px] tabular-nums transition ${
                    active ? 'bg-primary/15 text-primary' : 'text-faint hover:text-muted'
                  } disabled:opacity-30`}
                >
                  {index === 0 ? t(language, 'mapNow') : clock(hour?.time)}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* --- The reading for the selected hour ---------------------------- */}
      <SelectedReading hour={selectedHour} here={here} step={step} language={language} />

      {insight && (
        <div className="mt-3 flex items-start gap-2 border-t border-[rgb(var(--wx-tint)/0.07)] pt-3">
          <span aria-hidden="true" className="mt-[1px] shrink-0 text-[13px]">🧠</span>
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-[0.12em] text-faint">{t(language, 'weatherGptSays')}</div>
            <p data-map-insight className="mt-0.5 text-[12.5px] leading-relaxed text-ink-soft">{insight}</p>
          </div>
        </div>
      )}
    </Panel>
  )
}

/**
 * One place, coloured and sized by the active layer's reading.
 *
 * A place with no reading for this layer and step is drawn hollow and muted —
 * visibly a gap rather than a low value, which is the difference between
 * missing data and calm weather.
 */
function LayerMarker({ entry, layer, step, language, isHere, onAsk }) {
  const value = valueAt(entry, layer, step)
  const known = value !== null
  const radius = isHere ? 11 : 6 + (known ? layer.scale(value) * 9 : 0)
  const color = known ? layer.ramp(value) : 'var(--color-faint)'
  const bearing = step === 0 && layer.bearingField ? entry[layer.bearingField] : null

  return (
    <>
      {/* A halo, so the reader's own place is unmistakable among the rest.
          Drawn as its own ring rather than by making the marker bigger, which
          would corrupt the size channel that carries the reading. */}
      {isHere && (
        <CircleMarker
          center={[entry.latitude, entry.longitude]}
          radius={radius + 8}
          interactive={false}
          pathOptions={{
            color: 'var(--color-primary)',
            weight: 1.5,
            opacity: 0.75,
            dashArray: '2 4',
            fillColor: 'var(--color-primary)',
            fillOpacity: 0.05,
          }}
        />
      )}
    <CircleMarker
      center={[entry.latitude, entry.longitude]}
      radius={radius}
      pathOptions={{
        color,
        weight: isHere ? 3 : 1.5,
        opacity: known ? 0.95 : 0.5,
        fillColor: color,
        fillOpacity: known ? 0.32 : 0.06,
        dashArray: known ? undefined : '3 3',
      }}
    >
      <Popup>
        <div className="text-[12px]">
          <div className="font-semibold">{entry.location}</div>
          {entry.admin1 && <div className="text-[11px] opacity-70">{entry.admin1}</div>}
          <div className="mt-1">
            {t(language, layer.labelKey)}:{' '}
            {known ? (
              <strong>
                {value.toFixed(layer.decimals)}
                {layer.unit}
              </strong>
            ) : (
              <em>{t(language, 'unavailable')}</em>
            )}
          </div>
          {typeof bearing === 'number' && (
            <div className="text-[11px] opacity-80">{t(language, 'direction')}: {Math.round(bearing)}°</div>
          )}
          <div className="mt-1 text-[11px] opacity-70">
            {t(language, 'riskScore')}: {entry.risk_score}/100 · {levelLabel(language, entry.risk_level)}
          </div>
          {/* The selection becomes the subject: this hands the place above to
              the assistant and leaves the conversation about it, not about
              wherever the reader was before they opened the map. */}
          {onAsk && (
            <button
              type="button"
              data-testid="ask-about-area"
              onClick={() => onAsk(entry)}
              className="mt-2 w-full rounded-lg border border-[rgb(var(--wx-tint)/0.3)] px-2 py-1.5
                         text-[11.5px] font-semibold text-ink transition
                         hover:bg-[rgb(var(--wx-tint)/0.12)]"
            >
              {t(language, 'askAboutArea')}
            </button>
          )}
        </div>
      </Popup>
    </CircleMarker>
    </>
  )
}

/** The selected hour's own numbers, for the selected place. Only real ones. */
function SelectedReading({ hour, here, step, language }) {
  const source = step === 0 ? here : hour
  if (!source) return null

  const rows = [
    ['🌧️', t(language, 'rainChance'), source.precipitation_probability_pct, '%'],
    ['💧', t(language, 'precipitation'), source.precipitation_mm, ' mm'],
    ['🌬️', t(language, 'wind'), source.wind_speed_kmh, ' km/h'],
    ['🌡️', t(language, 'feelsLike'), source.temperature_c, '°C'],
  ].filter(([, , value]) => typeof value === 'number')

  if (!rows.length) return null

  return (
    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 border-t border-[rgb(var(--wx-tint)/0.07)] pt-3">
      {rows.map(([icon, label, value, unit]) => (
        <span key={label} className="flex items-center gap-1.5 text-[11.5px] text-muted">
          <span aria-hidden="true">{icon}</span>
          <span>{label}</span>
          <strong className="tabular-nums text-ink">
            {Number(value).toFixed(unit === ' mm' ? 1 : 0)}
            {unit}
          </strong>
        </span>
      ))}
    </div>
  )
}

/** A scale that matches what is actually on the map, and nothing more. */
function Legend({ layer, language }) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <div className="flex items-center gap-1" aria-hidden="true">
        {[0.08, 0.35, 0.62, 0.9].map((fraction) => (
          <span
            key={fraction}
            className="h-2 w-5 rounded-sm"
            style={{
              background: layer.ramp(
                layer.id === 'temperature' ? 8 + fraction * 36 : fraction * (layer.id === 'wind' ? 60 : 100),
              ),
              opacity: 0.75,
            }}
          />
        ))}
      </div>
      <span className="truncate text-[10.5px] text-faint">
        {layer.legendKeys.map((key) => t(language, key)).join(' → ')}
      </span>
    </div>
  )
}
