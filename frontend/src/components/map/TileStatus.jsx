import { useCallback, useState } from 'react'
import { TileLayer } from 'react-leaflet'
import { t } from '../../i18n/ui'
import { useStore } from '../../store/useStore'

/**
 * The basemap, and what to say when it cannot be reached.
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

export default function TileStatus({ url, attribution }) {
  const language = useStore((s) => s.language)
  const [failures, setFailures] = useState(0)
  const [attempt, setAttempt] = useState(0)

  const retry = useCallback(() => { setFailures(0); setAttempt((n) => n + 1) }, [])

  return (
    <>
      <TileLayer
        // Remounting is what actually re-requests the tiles; Leaflet caches the
        // failures otherwise and a retry button would do nothing visible.
        key={attempt}
        url={url}
        attribution={attribution}
        eventHandlers={{ tileerror: () => setFailures((n) => n + 1) }}
      />
      {failures >= FAILURES_BEFORE_SAYING_SO && (
        <div
          role="status"
          className="pointer-events-auto absolute inset-x-3 top-3 z-[600] flex items-center justify-between gap-3
                     rounded-[var(--radius-card)] border border-[var(--wx-border)] bg-[var(--wx-surface)]
                     px-3 py-2 shadow-[var(--shadow-lift)]"
        >
          <span className="min-w-0 text-[12px] leading-snug text-ink-soft">
            {t(language, 'mapUnavailable')}
          </span>
          <button
            type="button"
            onClick={retry}
            className="shrink-0 text-[12px] font-semibold text-primary transition hover:opacity-80"
          >
            {t(language, 'retry')}
          </button>
        </div>
      )}
    </>
  )
}
