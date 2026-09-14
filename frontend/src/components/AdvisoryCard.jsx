import { motion } from 'framer-motion'
import { hazardLabel, levelLabel, t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import SpokenAdvice from './audio/SpokenAdvice'
import { STATUS, severityOf } from './ui/severity'
import Icon from './ui/Icon'

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
function WeatherImpact({ impacts, language, location, userType }) {
  if (!impacts?.length) return null
  const [mine, ...others] = impacts
  const tone = STATUS[mine.status] ?? STATUS.Safe

  return (
    <section
      data-testid="advisory-impact"
      className="mt-3 rounded-[var(--radius-control)] border border-[var(--wx-border)] bg-[var(--wx-surface)] p-3"
    >
      <h3 className="wx-eyebrow">{t(language, 'yourWeatherImpact')}</h3>

      <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-[12.5px] font-semibold text-ink">{mine.category}</span>
        <span
          className="flex items-center gap-1 rounded-[var(--radius-pill)] px-1.5 py-px text-[10px] font-semibold"
          style={{ color: tone.ink, background: tone.tint }}
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

      {/* Why it matters, said aloud — a different question from the actions
          above it, so a different sentence. */}
      <SpokenAdvice location={location} userType={userType} topic="impact" compact />

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

/**
 * The tint of the action card.
 *
 * The reference draws this card green, and green is right for what it is — the
 * card that says what to do, sitting under a card that says what is wrong. But
 * a fixed green would put "move to higher ground, water is entering your area"
 * on a reassuring ground, so the tint follows the band instead and green is
 * simply where a Low or Moderate day lands. On the reference's own weather this
 * renders exactly the reference's green.
 */
const ADVICE_TINT = {
  Low: { line: 'color-mix(in srgb, var(--color-safe) 26%, transparent)', fill: 'color-mix(in srgb, var(--color-safe) 7%, var(--wx-surface))', ink: 'var(--color-safe)' },
  Moderate: { line: 'color-mix(in srgb, var(--color-safe) 26%, transparent)', fill: 'color-mix(in srgb, var(--color-safe) 7%, var(--wx-surface))', ink: 'var(--color-safe)' },
  High: { line: 'color-mix(in srgb, var(--color-warning) 30%, transparent)', fill: 'color-mix(in srgb, var(--color-warning) 8%, var(--wx-surface))', ink: 'var(--color-warning)' },
  Severe: { line: 'color-mix(in srgb, var(--color-danger) 32%, transparent)', fill: 'color-mix(in srgb, var(--color-danger) 8%, var(--wx-surface))', ink: 'var(--color-danger)' },
}

export default function AdvisoryCard({ advisory, impacts, onCompare }) {
  const language = useStore((s) => s.language)
  const location = useStore((s) => s.location)
  const userType = useStore((s) => s.userType)

  // Optional field: an older client, or a calm day, simply renders nothing.
  if (!advisory?.actions?.length) return null

  const tone = severityOf(advisory.risk_level)
  const tint = ADVICE_TINT[advisory.risk_level] ?? ADVICE_TINT.Low

  return (
    <motion.section
      data-testid="advisory-card"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className="wx-note min-w-0 p-4"
      style={{ '--wx-note-line': tint.line, '--wx-note-fill': tint.fill }}
    >
      {/* --- Heading row ------------------------------------------------- */}
      <div className="flex min-w-0 items-start gap-2.5">
        <span
          className="mt-px grid h-8 w-8 shrink-0 place-items-center rounded-full text-on-solid"
          style={{ background: tint.ink }}
        >
          <Icon name="shield" size={17} stroke={1.9} />
        </span>

        <div className="min-w-0 flex-1">
          <h2 className="text-[14.5px] font-bold leading-tight tracking-[-0.01em] text-ink">
            {t(language, 'advisoryTitle')}
          </h2>
          <div className="mt-1 flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1">
            <span aria-hidden="true" className="text-[10px]" style={{ color: tone.ink }}>{tone.icon}</span>
            <span className="text-[11.5px] font-semibold text-ink-soft">
              {hazardLabel(language, advisory.hazard)}
            </span>
            <span className="text-[11px] text-muted">· {levelLabel(language, advisory.risk_level)}</span>
          </div>
        </div>

        {onCompare && (
          <button
            type="button"
            onClick={onCompare}
            className="mt-px shrink-0 rounded-[var(--radius-pill)] bg-[rgb(var(--wx-tint)/0.09)] px-2.5 py-1
                       text-[10.5px] font-semibold text-primary transition hover:bg-[rgb(var(--wx-tint)/0.16)]"
          >
            {t(language, 'comparePersonas')} →
          </button>
        )}
      </div>

      {/* What is happening. Sits above the actions because it is the thing the
          actions are about, and stays one line: the forecast has panels of its
          own and this is not one of them. */}
      {advisory.situation && (
        <p data-testid="advisory-situation" className="mt-3 text-[13px] leading-[1.5] text-ink-soft">
          {advisory.situation}
        </p>
      )}

      {/* The list is ranked, so it is set ranked: the first action gets the
          weight, the rest are visibly support. A list where every line shouts
          equally is a list a reader has to triage themselves, which is the
          work this panel exists to have already done. */}
      <ol className="mt-3 space-y-2.5">
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
              <span aria-hidden="true" className="wx-step mt-[2px]">
                {String(item.priority ?? index + 1).padStart(2, '0')}
              </span>
              <div className="min-w-0">
                <p className={lead
                  ? 'text-[13.5px] font-semibold leading-[1.45] text-ink'
                  : 'text-[12.5px] leading-[1.45] text-ink-soft'}>
                  {item.action}
                </p>
                {item.reason && (
                  <p className="mt-0.5 text-[11px] leading-[1.45] text-muted">
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
          paraphrase of the advice above. */}
      {advisory.reason && (
        <p data-testid="advisory-reason" className="mt-3 text-[11px] leading-[1.5] text-muted">
          <span className="font-semibold text-ink-soft">{t(language, 'becauseLabel')}: </span>
          {advisory.reason}
        </p>
      )}

      <WeatherImpact
        impacts={impacts}
        language={language}
        location={location?.name}
        userType={userType}
      />

      {/* The same actions, said out loud. Sits with the advice rather than in
          a toolbar somewhere: hearing it is one of the ways to read it. */}
      <SpokenAdvice location={location?.name} userType={userType} />

      {advisory.disclaimer && (
        <p className="mt-3 border-t border-[rgb(var(--wx-tint)/0.09)] pt-2.5 text-[10.5px] leading-[1.45] text-faint">
          {advisory.disclaimer}
        </p>
      )}
    </motion.section>
  )
}
