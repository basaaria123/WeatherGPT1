import { useCallback, useEffect, useMemo, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { CircleMarker, MapContainer, TileLayer, ZoomControl, useMap, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { levelLabel, t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import RiskDetail from './map/RiskDetail'
import { severityOf } from './ui/severity'
import { EmptyState, Panel, SeverityPill, Skeleton } from './ui/Primitives'

/**
 * India risk map — the exploration layer.
 *
 * Markers are sized and coloured from the risk-map endpoint, which reads the
 * same engine as the alerts and the chat answer. Circle markers rather than
 * pin images: no asset to load, and radius carries the score as a second
 * channel alongside colour.
 *
 * Selecting a place happens in two steps, and the map has exactly three states:
 *
 *   1. nothing selected — the country, and a line asking for a place
 *   2. a marker selected — a preview box; the reader has not moved, and the
 *      dashboard is still showing whatever it was showing before
 *   3. "View local details" pressed — the place becomes the one active
 *      WeatherGPT location, and the reader lands back on the home page
 *
 * The distinction between 2 and 3 is the reason this component holds a
 * selection of its own. It is a *name*, not a copy of the entry: the box always
 * renders from the current payload, so a refresh underneath it updates it
 * instead of leaving it stale. And it is deliberately local — the store keeps
 * one location, the active one, which the dashboard, forecast, risk panel and
 * chat all read. A second location in the store is exactly the confusion this
 * flow exists to avoid.
 */

const INDIA_CENTER = [22.6, 79.5]
const DEFAULT_ZOOM = 4

// Carto's dark basemap suits the palette and needs no API key.
const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'

// How much bigger the previewed marker is drawn than an unselected one.
const SELECTED_BUMP = 5

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

/**
 * Keeps the selected marker clear of the preview box.
 *
 * The box is a bottom sheet on a narrow screen and a top-left card on a wide
 * one, and either can land on top of the very marker the reader just pressed.
 * Being unable to see where the selection is defeats the point of a map, so the
 * map pans by however much of it the box is covering — and by nothing at all
 * when the marker is already in the clear.
 */
function KeepSelectionVisible({ entry }) {
  const map = useMap()
  useEffect(() => {
    if (!entry) return undefined
    // Measured after the box has been laid out, from the box itself rather
    // than from a guess at how tall it is: the content varies by location, and
    // a marker half under the sheet is the failure this exists to prevent.
    const timer = setTimeout(() => {
      const container = map.getContainer()
      const box = container.parentElement?.querySelector('[data-testid="risk-detail"]')
      if (!box) return
      const mapRect = container.getBoundingClientRect()
      const boxRect = box.getBoundingClientRect()
      const at = map.latLngToContainerPoint([entry.latitude, entry.longitude])
      // `at` is the marker's centre, so its own radius has to clear the box too
      // — otherwise the circle ends up half tucked under the sheet's top edge.
      const margin = radiusFor(entry.risk_score) + SELECTED_BUMP + 14

      let dx = 0
      let dy = 0
      if (boxRect.width > mapRect.width * 0.8) {
        // A sheet across the bottom: lift the marker clear of its top edge.
        const ceiling = boxRect.top - mapRect.top - margin
        if (at.y > ceiling) dy = at.y - ceiling
      } else {
        // A card down one side: push the marker out past it.
        const edge = boxRect.right - mapRect.left + margin
        if (at.x < edge) dx = at.x - edge
        if (at.y < margin) dy = at.y - margin
      }
      if (dx || dy) map.panBy([dx, dy], { animate: true, duration: 0.45 })
    }, 90)
    return () => clearTimeout(timer)
  }, [entry, map])
  return null
}

/** Clicking the map itself, rather than a marker, dismisses the preview. */
function DismissOnMapClick({ onDismiss }) {
  useMapEvents({ click: onDismiss })
  return null
}

export default function RiskMap({ data, loading, error, onRetry, onCommit }) {
  const language = useStore((s) => s.language)
  const mapFocus = useStore((s) => s.mapFocus)
  const activeName = useStore((s) => s.location?.name)
  const [mounted, setMounted] = useState(false)
  const [previewName, setPreviewName] = useState(null)

  // Leaflet needs a sized container; mounting after paint avoids a 0-height map.
  useEffect(() => {
    const timer = setTimeout(() => setMounted(true), 60)
    return () => clearTimeout(timer)
  }, [])

  const locations = useMemo(() => data?.locations ?? [], [data])
  const worst = locations[0]
  const preview = useMemo(
    () => locations.find((entry) => entry.location === previewName) ?? null,
    [locations, previewName],
  )

  const dismiss = useCallback(() => setPreviewName(null), [])

  // Step two, and the only thing here that moves the reader. The preview is
  // dropped on the way out so returning to the map starts from state 1.
  const commit = useCallback(() => {
    if (!preview) return
    setPreviewName(null)
    onCommit?.(preview)
  }, [preview, onCommit])

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

          <div className="relative h-[36rem] overflow-hidden rounded-xl border border-[rgb(var(--wx-tint)/0.08)] sm:h-[26rem]">
            {mounted && (
              <MapContainer
                center={INDIA_CENTER}
                zoom={DEFAULT_ZOOM}
                minZoom={3}
                maxZoom={9}
                scrollWheelZoom={false}
                style={{ height: '100%', width: '100%' }}
                attributionControl
                /* The detail card claims the top-left corner, which is where
                   Leaflet puts its zoom buttons by default — they landed on top
                   of the location's own name. */
                zoomControl={false}
              >
                <ZoomControl position="topright" />
                <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
                <FocusController focus={mapFocus} />
                <DismissOnMapClick onDismiss={dismiss} />
                <KeepSelectionVisible entry={preview} />
                {locations.map((entry) => {
                  const tone = severityOf(entry.risk_level)
                  // Two different things worth marking, and they must not look
                  // alike: the place being previewed right now, and the place
                  // the rest of the app is actually showing.
                  const isPreview = entry.location === previewName
                  const isActive = entry.location === activeName
                  return (
                    <CircleMarker
                      key={`${entry.location}-${entry.latitude}`}
                      center={[entry.latitude, entry.longitude]}
                      radius={radiusFor(entry.risk_score) + (isPreview ? SELECTED_BUMP : isActive ? 2 : 0)}
                      /* Without this the map's own click handler fires straight
                         after the marker's and closes the box that just opened. */
                      bubblingMouseEvents={false}
                      eventHandlers={{ click: () => setPreviewName(entry.location) }}
                      pathOptions={{
                        color: isPreview ? '#ffffff' : tone.color,
                        fillColor: tone.color,
                        fillOpacity: isPreview ? 0.78 : isActive ? 0.52 : 0.36,
                        weight: isPreview ? 3.5 : isActive ? 2.5 : 1.6,
                        dashArray: isActive && !isPreview ? '3 3' : undefined,
                      }}
                    />
                  )
                })}
              </MapContainer>
            )}

            {/* Outside the map, so Leaflet neither swallows the clicks nor
                fights the box for stacking order. */}
            <AnimatePresence>
              {preview && (
                <RiskDetail
                  key={preview.location}
                  entry={preview}
                  isActive={preview.location === activeName}
                  activeName={activeName}
                  onCommit={commit}
                  onClose={dismiss}
                />
              )}
            </AnimatePresence>
          </div>

          {/* Legend repeats the icon so severity is never colour-only. */}
          <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5">
            {['Low', 'Moderate', 'High', 'Severe'].map((level) => {
              const tone = severityOf(level)
              return (
                <span key={level} className="flex items-center gap-1 text-[11px] text-muted">
                  <span aria-hidden="true" style={{ color: tone.color }}>{tone.icon}</span>
                  {levelLabel(language, level)}
                </span>
              )
            })}
            {data?.errors?.length > 0 && (
              <span className="ml-auto text-[11px] text-caution">
                {t(language, 'mapPartial').replace('{n}', data.errors.length)}
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
