import { motion } from 'framer-motion'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { Panel } from './ui/Primitives'

/**
 * Historical context — deliberately not an alert.
 *
 * This panel is styled unlike the alert cards on purpose: a pattern match
 * against a past event is context, and must never be mistaken for an active
 * warning about now. It renders below both the answer and any live alert.
 *
 * The matched dimensions are shown with both values so a reader can check the
 * comparison rather than trust it. That transparency is what separates this
 * from a spooky assertion.
 */
export default function HistoricalContext({ similarity }) {
  const language = useStore((s) => s.language)

  // Optional field, and silent unless the score clears the backend threshold.
  if (!similarity?.matched) return null

  const { event = {}, matching_dimensions: dimensions = [], similarity_score: score } = similarity

  return (
    <Panel
      id="historical-context"
      title={t(language, 'historicalTitle')}
      action={
        typeof score === 'number' ? (
          <span className="rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.14)]
                           px-2 py-0.5 text-[11px] font-semibold text-muted">
            {score}% similar
          </span>
        ) : null
      }
    >
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        // Neutral surface, no severity colour: this is not a warning.
        className="rounded-xl border border-[rgb(var(--wx-tint)/0.1)] bg-[rgb(var(--wx-tint)/0.03)] p-3.5"
      >
        <div className="mb-1.5 flex flex-wrap items-baseline gap-x-2">
          <h3 className="text-[13px] font-semibold text-ink">{event.name}</h3>
          {event.date_range && <span className="text-[11px] text-muted">{event.date_range}</span>}
          {event.region && <span className="text-[11px] text-faint">· {event.region}</span>}
        </div>

        {similarity.sentence && (
          <p className="text-[12px] leading-relaxed text-ink-soft">{similarity.sentence}</p>
        )}

        {dimensions.length > 0 && (
          <div className="mt-3 border-t border-[rgb(var(--wx-tint)/0.09)] pt-2.5">
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
              {t(language, 'matchedOn')}
            </p>
            <ul className="space-y-1.5">
              {dimensions.map((d) => (
                <li key={d.dimension} className="flex flex-wrap items-baseline gap-x-2 text-[11px]">
                  <span className="min-w-0 flex-1 truncate text-muted">{d.dimension}</span>
                  <span className="tabular-nums text-ink">
                    {d.current}{d.unit}
                  </span>
                  <span className="text-faint">vs {d.historical}{d.unit}</span>
                  <span className="tabular-nums font-semibold text-accent">{d.closeness_pct}%</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <p className="mt-3 border-t border-[rgb(var(--wx-tint)/0.09)] pt-2 text-[11px] leading-relaxed text-faint">
          {t(language, 'notPrediction')}
        </p>

        {event.source && (
          <p className="mt-1.5 text-[11px] text-faint">
            {t(language, 'sourceLabel')}: {event.source_url ? (
              <a
                href={event.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-2 transition hover:text-muted"
              >
                {event.source}
              </a>
            ) : event.source}
          </p>
        )}
      </motion.div>
    </Panel>
  )
}
