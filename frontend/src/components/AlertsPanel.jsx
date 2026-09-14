import { AnimatePresence } from 'framer-motion'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import AlertCard from './alerts/AlertCard'
import Icon from './ui/Icon'

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
    <div className="min-w-0 space-y-2.5">
      {/* Said once, at the top, because every row below is this app's own
          reading rather than a warning an agency issued. */}
      <p className="px-1 text-[10.5px] leading-[1.45] text-faint">{t(language, 'aiHazardNote')}</p>

      {here.length === 0 ? (
        /* The reference's own empty state: a small green card that says the
           absence plainly, rather than a large panel of nothing. */
        <div
          className="wx-note flex min-w-0 items-center gap-3 p-3.5"
          style={{
            '--wx-note-line': 'color-mix(in srgb, var(--color-safe) 26%, transparent)',
            '--wx-note-fill': 'color-mix(in srgb, var(--color-safe) 6%, var(--wx-surface))',
          }}
        >
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-safe text-on-solid">
            <Icon name="check" size={18} stroke={2.1} />
          </span>
          <span className="min-w-0">
            <span className="block text-[13px] font-bold leading-tight text-ink">
              {t(language, 'noOtherAlerts')}
            </span>
            <span className="block text-[11.5px] text-muted">{t(language, 'noOtherAlertsBody')}</span>
          </span>
        </div>
      ) : (
        <ul className="min-w-0 space-y-2.5">
          <AnimatePresence initial={false}>
            {here.map((alert) => (
              <li key={alert.id} className="min-w-0">
                <AlertCard
                  alert={alert}
                  isNew={alert.id === lastAlertId}
                  onViewArea={onViewArea}
                />
              </li>
            ))}
          </AnimatePresence>
        </ul>
      )}

      {/* How often this list is refreshed, said where the list is — the
          reference prints it directly under the cards. */}
      <p className="flex items-center gap-1.5 px-1 text-[10.5px] text-faint">
        <Icon name="info" size={11} />
        {t(language, 'alertsUpdateNote')}
      </p>

      {elsewhere.length > 0 && (
        <details className="glass min-w-0 p-3.5">
          <summary className="wx-eyebrow cursor-pointer list-none transition hover:text-ink">
            {t(language, 'elsewhere')} · {elsewhere.length} ▾
          </summary>
          <ul className="scroll-y -mx-1 mt-2.5 max-h-[22rem] space-y-2.5 px-1">
            {elsewhere.map((alert) => (
              <li key={alert.id} className="min-w-0">
                <AlertCard
                  alert={alert}
                  isNew={alert.id === lastAlertId}
                  onViewArea={onViewArea}
                />
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}

