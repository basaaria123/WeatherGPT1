import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { Panel } from './ui/Primitives'

/**
 * "Best time to…" — the forecast's answer to *when*, on its own.
 *
 * The server already computes this: it is the role's own timing card, the one
 * that searches the hourly series for an hour and names it. It was reaching the
 * role panel on Home and nowhere else, which is the wrong place for it — a
 * question about when belongs with the hours.
 *
 * Renders nothing when the hourly series gives no answer. An empty "best time"
 * heading is worse than no heading: it reads as a failure rather than as a day
 * with no particular best hour in it.
 */
export default function BestTime({ bestTime }) {
  const language = useStore((s) => s.language)
  if (!bestTime?.headline) return null

  return (
    <Panel title={t(language, 'bestTimeTo')}>
      <div className="flex min-w-0 items-start gap-3">
        <span aria-hidden="true" className="mt-[1px] shrink-0 text-[18px]">🕗</span>
        <div className="min-w-0">
          {bestTime.title && (
            <p className="text-[11px] uppercase tracking-[0.12em] text-faint">{bestTime.title}</p>
          )}
          <p className="mt-0.5 text-[16px] font-semibold text-ink">{bestTime.headline}</p>
          {bestTime.detail && (
            <p className="mt-1 text-[12.5px] leading-relaxed text-muted">{bestTime.detail}</p>
          )}
        </div>
      </div>
    </Panel>
  )
}
