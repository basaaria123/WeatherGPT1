import { t } from '../i18n/ui'
import { severityRank, useStore } from '../store/useStore'
import AlertCard from './alerts/AlertCard'
import Icon from './ui/Icon'

/**
 * The live warning at the top of Home.
 *
 * The reference puts a full warning card here — badge, title, place, window,
 * expected impact, recommendation, and two buttons — not a one-line link, so
 * that is what this renders, through the same `AlertCard` the Alerts
 * destination uses. One card, two screens, one look.
 *
 * It still renders *nothing at all* when nothing is live. An absence does not
 * need a card, and on the ordinary day — most days — a reader should not scroll
 * past a large panel saying that nothing is wrong.
 *
 * Only the worst warning is shown, with a line beneath counting the rest. The
 * whole list is the Alerts destination's job.
 */
export default function AlertIndicator({ onOpen, onViewArea }) {
  const language = useStore((s) => s.language)
  const alerts = useStore((s) => s.alerts)
  const lastAlertId = useStore((s) => s.lastAlertId)
  const location = useStore((s) => s.location)

  // Warnings for the place on screen. One issued for a city three states away
  // is not what this is for, and counting it would make the number a lie about
  // where the reader is.
  const selected = location?.name?.trim().toLowerCase() ?? ''
  const here = alerts.filter((alert) => {
    const name = alert.location?.trim().toLowerCase() ?? ''
    return selected && name && (name.includes(selected) || selected.includes(name))
  })

  if (here.length === 0) return null

  // The worst one leads, because that is the one that decides what to do.
  const worst = here.reduce((a, b) => (severityRank[b.severity] > severityRank[a.severity] ? b : a))

  return (
    <div data-testid="alert-indicator" className="min-w-0 space-y-1.5">
      <AlertCard
        alert={worst}
        isNew={worst.id === lastAlertId}
        onViewDetails={onOpen}
        onViewArea={onViewArea}
      />

      <button
        type="button"
        onClick={onOpen}
        className="flex w-full items-center gap-1.5 px-1 text-[11px] font-semibold text-primary
                   transition hover:opacity-75"
      >
        <Icon name="warning" size={12} />
        <span>
          {here.length} {t(language, 'activeAlerts').toLowerCase()}
        </span>
        <span className="text-faint">·</span>
        <span>{t(language, 'viewAll')}</span>
      </button>
    </div>
  )
}
