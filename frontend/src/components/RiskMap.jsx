import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { severityOf } from './ui/severity'
import { EmptyState, Panel, SeverityPill, Skeleton } from './ui/Primitives'

/**
 * India risk map.
 *
 * Markers are sized and coloured from the risk-map endpoint, which reads the
 * same engine as the alerts and the chat answer. Circle markers rather than
 * pin images: no asset to load, and radius carries the score as a second
 * channel alongside colour.
 */

const INDIA_CENTER = [22.6, 79.5]
const DEFAULT_ZOOM = 4

// Carto's dark basemap suits the palette and needs no API key.
const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'

function radiusFor(score) {
  return 6 + (Math.max(0, Math.min(100, score)) / 100) * 13
}

/** Pans the map when an alert's "View affected area" is used. */
function FocusController({ focus }) {
  const map = useMap()
  useEffect(() => {
    if (focus?.latitude !== undefined && focus?.latitude !== null) {
      map.flyTo([focus.latitude, focus.longitude], 7, { duration: 1.1 })
    }
  }, [focus, map])
  return null
}

export default function RiskMap({ data, loading, error, onRetry, onSelect }) {
  const language = useStore((s) => s.language)
  const mapFocus = useStore((s) => s.mapFocus)
  const selectedName = useStore((s) => s.location?.name)
  const [mounted, setMounted] = useState(false)

  // Leaflet needs a sized container; mounting after paint avoids a 0-height map.
  useEffect(() => {
    const timer = setTimeout(() => setMounted(true), 60)
    return () => clearTimeout(timer)
  }, [])

  const locations = useMemo(() => data?.locations ?? [], [data])
  const worst = locations[0]

  return (
    <Panel
      id="risk-map"
      title={t(language, 'riskMap')}
      action={
        worst ? (
          <SeverityPill level={worst.risk_level} label={worst.location} score={worst.risk_score} compact />
        ) : null
      }
    >
      {loading && !locations.length ? (
        <Skeleton className="h-[19rem] w-full" />
      ) : error && !locations.length ? (
        <EmptyState icon="!" message={error} />
      ) : (
        <>
          <p className="mb-2 text-[11px] leading-relaxed text-muted">{t(language, 'mapHint')}</p>

          <div className="relative h-[19rem] overflow-hidden rounded-xl border border-[rgb(var(--wx-tint)/0.08)] sm:h-[23rem]">
            {mounted && (
              <MapContainer
                center={INDIA_CENTER}
                zoom={DEFAULT_ZOOM}
                minZoom={3}
                maxZoom={9}
                scrollWheelZoom={false}
                style={{ height: '100%', width: '100%' }}
                attributionControl
              >
                <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
                <FocusController focus={mapFocus} />
                {locations.map((entry) => {
                  const tone = severityOf(entry.risk_level)
                  // The place the dashboard is showing gets a heavier ring, so
                  // the map and the rest of the page visibly agree.
                  const isSelected = entry.location === selectedName
                  return (
                    <CircleMarker
                      key={`${entry.location}-${entry.latitude}`}
                      center={[entry.latitude, entry.longitude]}
                      radius={radiusFor(entry.risk_score) + (isSelected ? 3 : 0)}
                      pathOptions={{
                        color: isSelected ? '#ffffff' : tone.color,
                        fillColor: tone.color,
                        fillOpacity: isSelected ? 0.6 : 0.36,
                        weight: isSelected ? 3 : 1.6,
                      }}
                    >
                      <Popup>
                        <div className="min-w-[9rem]">
                          <p className="text-[13px] font-semibold text-ink">{entry.location}</p>
                          {entry.admin1 && <p className="text-[11px] text-muted">{entry.admin1}</p>}
                          <p className="mt-1.5 text-[11px] text-ink-soft">
                            <span aria-hidden="true" style={{ color: tone.color }}>{tone.icon}</span>{' '}
                            {entry.risk_level} · {entry.risk_score}/100
                          </p>
                          {entry.detected_hazard !== 'None' && (
                            <p className="text-[11px] text-muted">{entry.detected_hazard}</p>
                          )}
                          {onSelect && !isSelected && (
                            <button
                              type="button"
                              onClick={() => onSelect(entry)}
                              className="mt-2 w-full rounded-lg border border-[rgb(var(--wx-tint)/0.15)] bg-[rgb(var(--wx-tint)/0.06)]
                                         px-2 py-1 text-[11px] font-medium text-ink transition
                                         hover:border-[rgb(var(--wx-tint)/0.30)] hover:bg-[rgb(var(--wx-tint)/0.12)]"
                            >
                              {t(language, 'openLocalDetail')} →
                            </button>
                          )}
                          {isSelected && (
                            <p className="mt-1.5 text-[11px] font-semibold text-primary">
                              {t(language, 'shownAbove')}
                            </p>
                          )}
                        </div>
                      </Popup>
                    </CircleMarker>
                  )
                })}
              </MapContainer>
            )}
          </div>

          {/* Legend repeats the icon so severity is never colour-only. */}
          <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5">
            {['Low', 'Moderate', 'High', 'Severe'].map((level) => {
              const tone = severityOf(level)
              return (
                <span key={level} className="flex items-center gap-1 text-[11px] text-muted">
                  <span aria-hidden="true" style={{ color: tone.color }}>{tone.icon}</span>
                  {level}
                </span>
              )
            })}
            {data?.errors?.length > 0 && (
              <span className="ml-auto text-[11px] text-caution">
                {data.errors.length} location(s) unavailable
              </span>
            )}
            {onRetry && (
              <button type="button" onClick={onRetry} className="ml-auto text-[11px] text-muted underline">
                {t(language, 'retry')}
              </button>
            )}
          </div>
        </>
      )}
    </Panel>
  )
}
