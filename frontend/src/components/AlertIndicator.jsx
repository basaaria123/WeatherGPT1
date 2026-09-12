import { t } from '../i18n/ui'
import { severityRank, useStore } from '../store/useStore'
import { severityOf } from './ui/severity'

/**
 * A live official warning, stated in one line at the foot of Home.
 *
 * Home used to carry the whole alerts panel, which meant that on the ordinary
 * day — most days — a reader scrolled past a large card saying nothing was
 * wrong. An absence does not need a card. So this renders *nothing at all*
 * when nothing is live, and one tappable line when something is.
 *
 * It reads the same store the Alerts destination reads, so the count here and
 * the list there cannot disagree. Tapping it goes to that list rather than
 * expanding in place: Home answers "what should I do now", and the detail of a
 * warning is a different question.
 */
export default function AlertIndicator({ onOpen }) {
  const language = useStore((s) => s.language)
  const alerts = useStore((s) => s.alerts)
  const location = useStore((s) => s.location)

  // Warnings for the place on screen. One issued for a city three states away
  // is not what this line is for, and counting it would make the number a lie
  // about where the reader is.
  const selected = location?.name?.trim().toLowerCase() ?? ''
  const here = alerts.filter((alert) => {
    const name = alert.location?.trim().toLowerCase() ?? ''
    return selected && name && (name.includes(selected) || selected.includes(name))
  })

  if (here.length === 0) return null

  // The worst one leads, because that is the one that decides what to do.
  const worst = here.reduce((a, b) => (severityRank[b.severity] > severityRank[a.severity] ? b : a))
  const tone = severityOf(worst.severity)

  return (
    <button
      type="button"
      onClick={onOpen}
      data-testid="alert-indicator"
      className="flex w-full min-w-0 items-center gap-3 rounded-[var(--radius-card)] border px-3.5 py-3 text-left
                 transition hover:brightness-[0.98]"
      style={{ borderColor: tone.ring, background: tone.tint }}
    >
      <span aria-hidden="true" className="text-[13px] leading-none" style={{ color: tone.ink }}>
        {tone.icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[12px] font-semibold" style={{ color: tone.ink }}>
          {here.length} · {t(language, 'aiHazard')}
        </span>
        <span className="mt-0.5 block truncate text-[13px] font-medium text-ink">
          {worst.hazard_label ?? worst.alert_type}
        </span>
      </span>
      <span className="shrink-0 text-[12px] font-medium text-muted">
        {t(language, 'viewAlert')} <span aria-hidden="true">→</span>
      </span>
    </button>
  )
}
