import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { userMessage } from '../api/errors'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import AlertsPanel from './AlertsPanel'
import NotificationSettings from './settings/NotificationSettings'
import { EmptyState, ErrorState, LoadingBlock, Panel, SeverityPill } from './ui/Primitives'
import { severityOf } from './ui/severity'

/**
 * The alerts destination: what is live, what has been, and what reaches you.
 *
 * Three tabs rather than three screens, because they are three views of one
 * subject and a reader moving between them is comparing, not navigating.
 *
 *   Active    the warnings in force for this place, right now
 *   History   the same store with the time filter lifted — a real record, not
 *             a second list that could drift from the first
 *   Settings  how a warning reaches you when the app is closed
 */

const TABS = [
  { id: 'active', label: 'tabActive' },
  { id: 'history', label: 'tabHistory' },
  { id: 'settings', label: 'tabSettings' },
]

export default function AlertsCenter({ onViewArea, onSignIn }) {
  const language = useStore((s) => s.language)
  const [tab, setTab] = useState('active')

  return (
    <>
      <div
        role="tablist"
        aria-label={t(language, 'aiHazard')}
        className="flex min-w-0 gap-1 rounded-[var(--radius-card)] border border-[var(--wx-border)] bg-[var(--wx-surface)] p-1"
      >
        {TABS.map((item) => {
          const active = tab === item.id
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              id={`alerts-tab-${item.id}`}
              aria-selected={active}
              aria-controls={`alerts-panel-${item.id}`}
              onClick={() => setTab(item.id)}
              className={`min-w-0 flex-1 truncate rounded-[calc(var(--radius-card)-0.25rem)] px-3 py-2
                          text-[12.5px] font-semibold transition
                          ${active
                            ? 'bg-primary text-white'
                            : 'text-muted hover:bg-[rgb(var(--wx-tint)/0.05)] hover:text-ink'}`}
            >
              {t(language, item.label)}
            </button>
          )
        })}
      </div>

      <div role="tabpanel" id={`alerts-panel-${tab}`} aria-labelledby={`alerts-tab-${tab}`}>
        {tab === 'active' && <AlertsPanel onViewArea={onViewArea} />}
        {tab === 'history' && <AlertHistory />}
        {tab === 'settings' && <NotificationSettings onSignIn={onSignIn} />}
      </div>
    </>
  )
}

/**
 * Everything the store has recorded for this place, live or lapsed.
 *
 * Fetched when the tab is opened rather than with the dashboard: it is the one
 * view nobody needs until they ask for it, and a reader who never opens it
 * should not pay for the request.
 */
function AlertHistory() {
  const language = useStore((s) => s.language)
  const location = useStore((s) => s.location)
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setError(null)
    setRows(null)
    try {
      const data = await api.alerts({
        location: location?.name,
        language,
        include_expired: true,
        limit: 50,
      })
      setRows(data?.alerts ?? [])
    } catch (err) {
      setError(userMessage(err, language))
    }
  }, [location?.name, language])

  useEffect(() => { load() }, [load])

  if (error) {
    return (
      <Panel title={t(language, 'tabHistory')}>
        <ErrorState message={error} onRetry={load} retryLabel={t(language, 'retry')} />
      </Panel>
    )
  }

  if (rows === null) {
    return (
      <Panel title={t(language, 'tabHistory')}>
        <LoadingBlock label={t(language, 'insightLoading')} lines={3} />
      </Panel>
    )
  }

  return (
    <Panel title={t(language, 'tabHistory')} action={
      rows.length > 0 ? <span className="text-[11px] font-semibold text-muted">{rows.length}</span> : null
    }>
      {rows.length === 0 ? (
        <EmptyState icon="○" message={t(language, 'alertHistoryEmpty')} />
      ) : (
        <ol className="space-y-1.5">
          {rows.map((alert) => <HistoryRow key={alert.id} alert={alert} language={language} />)}
        </ol>
      )}
    </Panel>
  )
}

function HistoryRow({ alert, language }) {
  const tone = severityOf(alert.severity)
  const when = (() => {
    const at = new Date(alert.timestamp)
    if (Number.isNaN(at.getTime())) return ''
    return at.toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  })()

  return (
    <li className="flex min-w-0 items-start gap-2.5 border-b border-[var(--wx-border)] py-2 last:border-b-0">
      <span aria-hidden="true" className="mt-[3px] shrink-0 text-[10px]" style={{ color: tone.ink }}>
        {tone.icon}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <span className="truncate text-[13px] font-semibold text-ink">
            {alert.hazard_label ?? alert.alert_type}
          </span>
          <SeverityPill
            level={alert.severity}
            label={alert.severity_label ?? alert.severity}
            compact
          />
        </div>
        <p className="mt-0.5 truncate text-[11.5px] text-muted">
          {alert.location}{when ? ` · ${when}` : ''}
        </p>
      </div>
      {/* Provenance on every row. It reads "WeatherGPT" because that is what
          produced it — no government feed is connected, and a row that implied
          one would be the misrepresentation this product must never make. */}
      <span className="shrink-0 text-[10px] uppercase tracking-[0.1em] text-faint">
        WeatherGPT
      </span>
    </li>
  )
}
