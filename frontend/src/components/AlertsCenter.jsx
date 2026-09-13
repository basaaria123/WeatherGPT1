import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { userMessage } from '../api/errors'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import AlertsPanel from './AlertsPanel'
import NotificationSettings from './settings/NotificationSettings'
import { EmptyState, ErrorState, LoadingBlock, Panel, SeverityPill, Tabs } from './ui/Primitives'
import { severityOf } from './ui/severity'
import Icon from './ui/Icon'

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
  const alerts = useStore((s) => s.alerts)
  const location = useStore((s) => s.location)

  // Warnings in force for the place on screen — what the "Active" count means.
  const selected = location?.name?.trim().toLowerCase() ?? ''
  const liveHere = alerts.filter((alert) => {
    const name = alert.location?.trim().toLowerCase() ?? ''
    return selected && name && (name.includes(selected) || selected.includes(name))
  }).length

  return (
    <>
      <Tabs
        idPrefix="alerts-tab"
        ariaLabel={t(language, 'aiHazard')}
        value={tab}
        onChange={setTab}
        items={TABS.map((item) => ({
          id: item.id,
          label: t(language, item.label),
          // Only the live tab carries a count, and it is the same list the
          // panel below renders — one source, so the number on the tab can
          // never disagree with the screen behind it.
          count: item.id === 'active' ? liveHere : 0,
        }))}
      />

      <div role="tabpanel" id={`alerts-tab-panel-${tab}`} aria-labelledby={`alerts-tab-${tab}`} className="mt-2.5 space-y-2.5">
        {tab === 'active' && (
          <>
            <AlertsPanel onViewArea={onViewArea} />
            {/* The reference prints a short history under the live list rather
                than leaving the foot of the screen empty, and "View all" is
                the tab beside it. Five rows, not fifty. */}
            <AlertHistory limit={5} onViewAll={() => setTab('history')} />
          </>
        )}
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
function AlertHistory({ limit = 50, onViewAll }) {
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
        limit,
      })
      setRows(data?.alerts ?? [])
    } catch (err) {
      setError(userMessage(err, language))
    }
  }, [location?.name, language, limit])

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
    <Panel
      title={t(language, 'alertHistory')}
      action={
        onViewAll ? (
          <button
            type="button"
            onClick={onViewAll}
            className="shrink-0 text-[11px] font-semibold text-primary transition hover:opacity-75"
          >
            {t(language, 'viewAll')}
          </button>
        ) : rows.length > 0 ? (
          <span className="text-[11px] font-semibold text-muted">{rows.length}</span>
        ) : null
      }
    >
      {rows.length === 0 ? (
        <EmptyState icon="○" message={t(language, 'alertHistoryEmpty')} />
      ) : (
        <ol className="min-w-0">
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
    <li className="flex min-w-0 items-center gap-2.5 border-b border-[var(--wx-border)] py-2.5 last:border-b-0">
      <span
        className="grid h-7 w-7 shrink-0 place-items-center rounded-full"
        style={{ background: tone.tint, color: tone.ink }}
      >
        <Icon name="warning" size={13} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[12.5px] font-bold text-ink">
          {alert.hazard_label ?? alert.alert_type}
        </p>
        {/* Provenance on every row. It reads "WeatherGPT" because that is what
            produced it — no government feed is connected, and a row that
            implied one would be the misrepresentation this product must never
            make. */}
        <p className="truncate text-[11px] text-muted">
          {alert.location}{when ? ` · ${when}` : ''} · WeatherGPT
        </p>
      </div>
      <SeverityPill
        level={alert.severity}
        label={alert.severity_label ?? alert.severity}
        compact
      />
    </li>
  )
}
