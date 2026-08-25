import { motion } from 'framer-motion'
import { Panel } from './ui/Primitives'

/**
 * Historical event comparison.
 *
 * Shown prominently but framed carefully: the heading says "historical
 * context", the backend's own sentence already disclaims prediction, and the
 * source note is always visible. The component renders backend text verbatim
 * and never composes a comparison of its own.
 */
export default function HistoricalNote({ comparison }) {
  if (!comparison) return null

  return (
    <Panel>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className="rounded-xl border border-accent/25 bg-accent/[0.07] p-4"
      >
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span
            aria-hidden="true"
            className="grid h-6 w-6 place-items-center rounded-md bg-accent/15 text-[11px] text-accent"
          >
            ⏱
          </span>
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-accent">
            Historical context — not a forecast
          </h2>
          <span className="ml-auto text-[11px] text-muted">
            {comparison.similarity_score}% similarity
          </span>
        </div>

        <p className="text-[13px] leading-relaxed text-ink-soft">{comparison.sentence}</p>

        <p className="mt-2.5 border-t border-white/[0.09] pt-2 text-[11px] leading-relaxed text-faint">
          {comparison.event_name} · {comparison.region} · {comparison.source_note}
        </p>
      </motion.div>
    </Panel>
  )
}
