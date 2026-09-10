import { motion } from 'framer-motion'
import { hazardLabel, levelLabel, t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import SpokenAdvice from './audio/SpokenAdvice'
import { STATUS, severityOf } from './ui/severity'
import { Panel } from './ui/Primitives'

/**
 * Persona advisory.
 *
 * Renders the backend's `advisory` block as-is. The actions come from a
 * deterministic rules table keyed by (hazard, user_type) — nothing here selects
 * or rewrites them, so what a reviewer reads in the rules file is exactly what
 * a citizen sees on screen.
 *
 * It answers three questions in the order a reader has them:
 *
 *   what is happening?     the situation line — the measured thing that is
 *                          happening or about to, with its own clock time
 *   what should I do?      the actions, the lead one carrying the most weight
 *   why am I told this?    the drivers, as the numbers the engine actually
 *                          scored — not a restatement of the advice
 *
 * The middle one is the point of the panel and is set largest. The other two
 * are context for it, not competitors with it.
 */
/**
 * What the weather means for this reader, in one line.
 *
 * The backend orders the impact cards by this profile's own categories, so the
 * first is theirs and the rest are context. It used to be three equal cards
 * with a screen to themselves, which put a generic "Travel: Caution" at the
 * same weight as the fisherman's own verdict and a scroll away from the advice
 * it relates to. Here the reader's own reading is a sentence, and the others
 * are chips — present, and visibly not the point.
 *
 * It says what the actions do not: an action is a next step, this is the
 * consequence that makes the step worth taking.
 */
function WeatherImpact({ impacts, language }) {
  if (!impacts?.length) return null
  const [mine, ...others] = impacts
  const tone = STATUS[mine.status] ?? STATUS.Safe

  return (
    <section
      data-testid="advisory-impact"
      className="mt-3 rounded-xl border border-[rgb(var(--wx-tint)/0.09)] bg-[rgb(var(--wx-tint)/0.03)] p-3"
    >
      <h3 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">
        {t(language, 'yourWeatherImpact')}
      </h3>

      <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-[12.5px] font-semibold text-ink">{mine.category}</span>
        <span
          className="flex items-center gap-1 rounded-[var(--radius-pill)] px-1.5 py-px text-[10px] font-semibold"
          style={{ color: tone.color, background: tone.tint }}
        >
          <span aria-hidden="true">{tone.icon}</span>
          {mine.headline}
        </span>
        <span className="rounded-[var(--radius-pill)] border border-primary/30 bg-primary/10 px-1.5 py-px
                         text-[10px] font-semibold text-primary">
          {t(language, 'forYou')}
        </span>
      </div>

      <p className="mt-1 text-[12px] leading-relaxed text-ink-soft">{mine.detail}</p>

      {/* Everyone else's, small enough that they cannot compete with it. */}
      {others.length > 0 && (
        <ul className="mt-2 flex flex-wrap gap-1.5">
          {others.map((item) => {
            const other = STATUS[item.status] ?? STATUS.Safe
            return (
              <li
                key={item.category}
                className="flex items-center gap-1 rounded-[var(--radius-pill)]
                           border border-[rgb(var(--wx-tint)/0.10)] bg-[rgb(var(--wx-tint)/0.04)]
                           px-1.5 py-px text-[10.5px] text-muted"
              >
                <span aria-hidden="true" style={{ color: other.color }}>{other.icon}</span>
                {item.category}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

export default function AdvisoryCard({ advisory, impacts, onCompare }) {
  const language = useStore((s) => s.language)
  const location = useStore((s) => s.location)
  const userType = useStore((s) => s.userType)

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
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <span aria-hidden="true" style={{ color: tone.color }}>{tone.icon}</span>
        <span className="text-[12px] font-semibold text-ink">
          {hazardLabel(language, advisory.hazard)}
        </span>
        <span className="text-[11px] text-muted">· {levelLabel(language, advisory.risk_level)}</span>
      </div>

      {/* What is happening. Sits above the actions because it is the thing the
          actions are about, and stays one line: the forecast has panels of its
          own and this is not one of them. */}
      {advisory.situation && (
        <p data-testid="advisory-situation" className="mb-3 text-[13.5px] leading-relaxed text-ink-soft">
          {advisory.situation}
        </p>
      )}

      {/* The list is ranked, so it is set ranked: the first action gets the
          weight, the rest are visibly support. A list where every line shouts
          equally is a list a reader has to triage themselves, which is the
          work this panel exists to have already done. */}
      <ol className="space-y-2">
        {advisory.actions.map((item, index) => {
          const lead = index === 0
          return (
          <motion.li
            key={`${item.action}-${index}`}
            data-testid={lead ? 'advisory-lead' : 'advisory-support'}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: index * 0.06 }}
            className="flex gap-2.5"
          >
            <span
              aria-hidden="true"
              className={`mt-0.5 grid shrink-0 place-items-center rounded-full font-semibold tabular-nums ${
                lead
                  ? 'h-6 w-6 border border-primary/45 bg-primary/12 text-[11px] text-primary'
                  : 'h-5 w-5 border border-[rgb(var(--wx-tint)/0.16)] text-[10.5px] text-faint'
              }`}
            >
              {String(item.priority ?? index + 1).padStart(2, '0')}
            </span>
            <div className="min-w-0">
              <p className={lead
                ? 'text-[14.5px] font-medium leading-relaxed text-ink'
                : 'text-[12.5px] leading-relaxed text-ink-soft'}>
                {item.action}
              </p>
              {item.reason && (
                <p className="mt-0.5 text-[11px] leading-relaxed text-muted">
                  <span className="font-semibold">{t(language, 'reasonLabel')}: </span>
                  {item.reason}
                </p>
              )}
            </div>
          </motion.li>
          )
        })}
      </ol>

      {/* Why any of this was said — the values the engine scored, not a
          paraphrase of the advice above. Labelled rather than run together so
          it reads as evidence and not as another instruction. */}
      {advisory.reason && (
        <p data-testid="advisory-reason" className="mt-3 text-[11.5px] leading-relaxed text-muted">
          <span className="font-semibold text-ink-soft">{t(language, 'becauseLabel')}: </span>
          {advisory.reason}
        </p>
      )}

      <WeatherImpact impacts={impacts} language={language} />

      {/* The same actions, said out loud. Sits with the advice rather than in
          a toolbar somewhere: hearing it is one of the ways to read it. */}
      <SpokenAdvice location={location?.name} userType={userType} />

      {advisory.disclaimer && (
        <p className="mt-3 border-t border-[rgb(var(--wx-tint)/0.09)] pt-2 text-[11px] leading-relaxed text-faint">
          {advisory.disclaimer}
        </p>
      )}
    </Panel>
  )
}
