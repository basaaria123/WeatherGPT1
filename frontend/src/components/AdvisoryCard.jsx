import { motion } from 'framer-motion'
import { hazardLabel, t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { severityOf } from './ui/severity'
import { Panel } from './ui/Primitives'

/**
 * Persona advisory.
 *
 * Renders the backend's `advisory` block as-is. The actions come from a
 * deterministic rules table keyed by (hazard, user_type) — nothing here selects
 * or rewrites them, so what a reviewer reads in the rules file is exactly what
 * a citizen sees on screen.
 */
export default function AdvisoryCard({ advisory, onCompare }) {
  const language = useStore((s) => s.language)

  // Optional field: an older client, or a calm day, simply renders nothing.
  if (!advisory?.actions?.length) return null

  const tone = severityOf(advisory.risk_level)

  return (
    <Panel
      title={t(language, 'advisoryTitle')}
      action={
        onCompare ? (
          <button
            type="button"
            onClick={onCompare}
            className="rounded-[var(--radius-pill)] border border-primary/40 bg-primary/10 px-2.5 py-1
                       text-[11px] font-medium text-primary transition hover:bg-primary/20"
          >
            {t(language, 'comparePersonas')} →
          </button>
        ) : null
      }
    >
      <div className="mb-2.5 flex flex-wrap items-center gap-1.5">
        <span aria-hidden="true" style={{ color: tone.color }}>{tone.icon}</span>
        <span className="text-[12px] font-semibold text-ink">
          {hazardLabel(language, advisory.hazard)}
        </span>
        <span className="text-[11px] text-muted">· {advisory.risk_level}</span>
      </div>

      <ol className="space-y-2">
        {advisory.actions.map((item, index) => (
          <motion.li
            key={`${item.action}-${index}`}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: index * 0.06 }}
            className="flex gap-2.5"
          >
            <span
              aria-hidden="true"
              className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full
                         border border-[rgb(var(--wx-tint)/0.16)] text-[11px] font-semibold text-muted"
            >
              {item.priority ?? index + 1}
            </span>
            <div className="min-w-0">
              <p className="text-[13px] leading-relaxed text-ink">{item.action}</p>
              {item.reason && (
                <p className="mt-0.5 text-[11px] leading-relaxed text-muted">
                  <span className="font-semibold">{t(language, 'reasonLabel')}: </span>
                  {item.reason}
                </p>
              )}
            </div>
          </motion.li>
        ))}
      </ol>

      {advisory.disclaimer && (
        <p className="mt-3 border-t border-[rgb(var(--wx-tint)/0.09)] pt-2 text-[11px] leading-relaxed text-faint">
          {advisory.disclaimer}
        </p>
      )}
    </Panel>
  )
}
