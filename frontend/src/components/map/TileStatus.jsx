import { useCallback, useEffect, useState } from 'react'
import { TileLayer } from 'react-leaflet'
import { t } from '../../i18n/ui'
import { useStore } from '../../store/useStore'

/**
 * The basemap, and what to say when it cannot be reached.
 *
 * ON THE TWO BASEMAPS. Both maps used to name the light Carto sheet themselves,
 * which meant that in dark appearance the one part of the app that stayed lit
 * was the map — a bright rectangle of cartography inside a near-black page,
 * with the markers' own colours read against the wrong ground. Carto publishes
 * a dark counterpart of the same sheet under the same licence and attribution,
 * so the appearance picks between them, and it is picked HERE rather than at
 * the two call sites so the two maps cannot drift apart again.
 *
 * Leaflet's own failure is silent: tiles that never arrive leave an empty
 * coloured rectangle, which reads as a map of nowhere rather than as a map that
 * is missing. The markers are still drawn from data we already have, so the
 * page is not broken — it just needs to say which part is absent.
 *
 * What it must never say is *why* in developer terms. A tile host being
 * unreachable is our problem, not the reader's, and a configuration error on
 * screen is a bug in its own right.
 */
const FAILURES_BEFORE_SAYING_SO = 6

// Carto Voyager and Carto Dark Matter: the same geography — state and district
// boundaries, place names, roads — drawn for a bright ground and for a dark
// one. Both are keyless, so nothing here can fail for want of a credential.
const TILES = {
  light: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
  dark: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
}

const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors ' +
  '&copy; <a href="https://carto.com/attributions">CARTO</a>'

export default function TileStatus() {
  const language = useStore((s) => s.language)
  const appearance = useStore((s) => s.appearance)
  const url = TILES[appearance === 'dark' ? 'dark' : 'light']
  const [failures, setFailures] = useState(0)
  const [attempt, setAttempt] = useState(0)

  const retry = useCallback(() => { setFailures(0); setAttempt((n) => n + 1) }, [])

  // A different sheet is a different set of requests: the count of failures
  // belongs to the sheet that produced them, not to the map.
  useEffect(() => { setFailures(0) }, [url])

  return (
    <>
      <TileLayer
        // Remounting is what actually re-requests the tiles; Leaflet caches the
        // failures otherwise and a retry button would do nothing visible.
        key={`${url}-${attempt}`}
        url={url}
        attribution={ATTRIBUTION}
        eventHandlers={{ tileerror: () => setFailures((n) => n + 1) }}
      />
      {failures >= FAILURES_BEFORE_SAYING_SO && (
        <div
          role="status"
          /* Clear of Leaflet's zoom control, which owns the top-left corner. */
          /* Bottom-left, clear of the zoom control, the recentre button and
             the scale. A notice that the base cartography is missing must not
             sit on top of the weather, which is the part that did arrive. */
          className="pointer-events-auto absolute bottom-7 left-2.5 z-[600] flex max-w-[calc(100%-5rem)]
                     items-center gap-2 rounded-[var(--radius-pill)] border border-[var(--wx-border)]
                     bg-[var(--wx-surface)] px-2.5 py-1 shadow-[var(--shadow-glass)]"
        >
          <span className="min-w-0 truncate text-[10.5px] leading-snug text-muted">
            {t(language, 'mapUnavailable')}
          </span>
          <button
            type="button"
            onClick={retry}
            className="shrink-0 text-[10.5px] font-semibold text-primary transition hover:opacity-80"
          >
            {t(language, 'retry')}
          </button>
        </div>
      )}
    </>
  )
}
