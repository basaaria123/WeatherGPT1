import { AnimatePresence, motion } from 'framer-motion'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { severityOf, isActionable } from './ui/severity'
import { EmptyState, Panel, SeverityPill } from './ui/Primitives'

/**
 * Live alerts, fed by the /ws/alerts socket.
 *
 * Newly-arrived alerts animate in rather than appearing between renders, which
 * is what makes a push during a demo legible instead of invisible.
 */
export default function AlertsPanel({ onViewArea }) {
  const language = useStore((s) => s.language)
  const alerts = useStore((s) => s.alerts)
  const lastAlertId = useStore((s) => s.lastAlertId)
  const location = useStore((s) => s.location)

  // Warnings issued for the selected place are the panel's subject; the rest of
  // the country is context, kept visually separate so the two are never read as
  // one list. This is also what keeps the panel consistent with the location
  // the rest of the dashboard is showing.
  const here = []
  const elsewhere = []
  const selected = location?.name?.trim().toLowerCase() ?? ''
  alerts.forEach((alert) => {
    const name = alert.location?.trim().toLowerCase() ?? ''
    const matches = selected && name && (name.includes(selected) || selected.includes(name))
    ;(matches ? here : elsewhere).push(alert)
  })

  return (
    <Panel
      title={t(language, 'officialAlerts')}
      action={
        here.length > 0 ? (
          <span className="text-[11px] font-semibold text-muted">{here.length}</span>
        ) : null
      }
    >
      {here.length === 0 ? (
        <EmptyState icon="✓" message={t(language, 'noOfficialAlerts')} />
      ) : (
        <ul className="scroll-y -mx-1 max-h-[22rem] space-y-2 px-1">
          <AnimatePresence initial={false}>
            {here.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                language={language}
                isNew={alert.id === lastAlertId}
                onViewArea={onViewArea}
              />
            ))}
          </AnimatePresence>
        </ul>
      )}

      {elsewhere.length > 0 && (
        <details className="mt-2.5 border-t border-[rgb(var(--wx-tint)/0.07)] pt-2.5">
          <summary className="cursor-pointer list-none text-[11px] text-muted transition hover:text-ink">
            {t(language, 'elsewhere')} · {elsewhere.length} ▾
          </summary>
          <ul className="scroll-y -mx-1 mt-2 max-h-[16rem] space-y-2 px-1">
            {elsewhere.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                language={language}
                isNew={alert.id === lastAlertId}
                onViewArea={onViewArea}
              />
            ))}
          </ul>
        </details>
      )}
    </Panel>
  )
}

function AlertCard({ alert, language, isNew, onViewArea }) {
  const tone = severityOf(alert.severity)
  const urgent = isActionable(alert.severity)
  const actions = alert.actions_localised?.length ? alert.actions_localised : alert.actions

  return (
    <motion.li
      layout
      initial={{ opacity: 0, x: 18, scale: 0.98 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
      className="relative overflow-hidden rounded-xl border p-3"
      style={{ borderColor: tone.ring, background: tone.tint }}
    >
      {isNew && (
        <motion.span
          className="absolute inset-0 rounded-xl"
          style={{ background: tone.color, opacity: 0.16 }}
          initial={{ opacity: 0.3 }}
          animate={{ opacity: 0 }}
          transition={{ duration: 1.6 }}
        />
      )}

      <div className="relative flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span
              aria-hidden="true"
              className={urgent ? 'pulse-alert' : ''}
              style={{ color: tone.color }}
            >
              {tone.icon}
            </span>
            <span className="truncate text-[13px] font-semibold text-ink">
              {alert.hazard_label ?? alert.alert_type}
            </span>
            <SeverityPill
              level={alert.severity}
              label={alert.severity_label ?? alert.severity}
              score={alert.risk_score}
              compact
            />
          </div>
          <p className="mt-0.5 truncate text-[12px] text-muted">{alert.location}</p>
        </div>
      </div>

      <p className="relative mt-2 text-[12px] leading-relaxed text-ink-soft">{alert.message}</p>

      {actions?.length > 0 && (
        <ul className="relative mt-2 space-y-1 border-t border-[rgb(var(--wx-tint)/0.09)] pt-2">
          {actions.slice(0, 2).map((action, index) => (
            <li key={index} className="flex gap-1.5 text-[11px] leading-relaxed text-ink-soft">
              <span aria-hidden="true" style={{ color: tone.color }}>▸</span>
              <span className="min-w-0">{action}</span>
            </li>
          ))}
        </ul>
      )}

      {alert.historical_comparison && (
        <p className="relative mt-2 rounded-lg border border-[rgb(var(--wx-tint)/0.09)] bg-black/20 px-2 py-1.5 text-[11px] leading-relaxed text-muted">
          <span className="font-semibold text-ink-soft">Historical context · </span>
          {alert.historical_comparison.sentence}
        </p>
      )}

      <div className="relative mt-2 flex items-center justify-between gap-2">
        <time className="text-[11px] text-faint" dateTime={alert.timestamp}>
          {formatTime(alert.timestamp)}
        </time>
        {alert.latitude !== null && alert.latitude !== undefined && (
          <button
            type="button"
            onClick={() => onViewArea?.(alert)}
            className="rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.12)] bg-[rgb(var(--wx-tint)/0.05)] px-2 py-0.5
                       text-[11px] text-ink-soft transition hover:border-[rgb(var(--wx-tint)/0.28)]"
          >
            {t(language, 'viewArea')} →
          </button>
        )}
      </div>
    </motion.li>
  )
}

function formatTime(iso) {
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
}
