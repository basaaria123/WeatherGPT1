import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useMemo, useState } from 'react'
import { useReducedMotion } from '../../hooks/useReducedMotion'
import { t } from '../../i18n/ui'
import { useStore } from '../../store/useStore'
import { IdentityStep, LanguageStep, LocationStep, RoleStep } from './steps'

/**
 * Three questions, then the dashboard.
 *
 * Where are you, what do you do, and which language — nothing else, because
 * every extra question is a reader lost before they have seen the product. The
 * fourth panel is not a question: it offers to remember the answers, and guest
 * is a first-class way past it rather than a dismissal.
 *
 * Each step writes straight into the store the dashboard already reads, so
 * finishing onboarding leaves nothing to hand over.
 */

const STEPS = ['location', 'role', 'language', 'identity']

export default function Onboarding({ onDone, startAt = 'location' }) {
  const language = useStore((s) => s.language)
  const completeOnboarding = useStore((s) => s.completeOnboarding)
  const reduced = useReducedMotion()

  // Opening straight at the identity panel is how "sign in" from the header
  // reaches this flow without asking the three questions again.
  const [index, setIndex] = useState(() => Math.max(0, STEPS.indexOf(startAt)))
  const step = STEPS[index]

  const next = useCallback(() => {
    setIndex((current) => {
      if (current >= STEPS.length - 1) return current
      return current + 1
    })
  }, [])

  const back = useCallback(() => setIndex((current) => Math.max(0, current - 1)), [])

  const finish = useCallback(() => {
    completeOnboarding()
    onDone()
  }, [completeOnboarding, onDone])

  // Only the questions are counted: the identity panel is an offer, not a step
  // the reader has to complete.
  const shown = Math.min(index + 1, STEPS.length - 1)

  const body = useMemo(() => {
    switch (step) {
      case 'location':
        return <LocationStep onNext={next} />
      case 'role':
        return <RoleStep onNext={next} />
      case 'language':
        return <LanguageStep onNext={next} />
      default:
        return <IdentityStep onDone={finish} />
    }
  }, [step, next, finish])

  return (
    <main className="relative mx-auto flex min-h-dvh w-full max-w-2xl flex-col px-5 pb-12 pt-8 sm:px-8">
      <header className="flex items-center justify-between gap-4">
        <span className="text-[15px] font-semibold tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>
          Weather<span className="text-primary">GPT</span>
        </span>
        {step !== 'identity' && (
          <span className="text-[11px] uppercase tracking-[0.16em] text-faint">
            {t(language, 'onbStep')} {shown} {t(language, 'onbOf')} {STEPS.length - 1}
          </span>
        )}
      </header>

      {/* Progress is a rule, not a widget: three segments, one filled per
          answered question. */}
      {step !== 'identity' && (
        <div className="mt-4 flex gap-1.5" aria-hidden="true">
          {STEPS.slice(0, 3).map((id, position) => (
            <span
              key={id}
              className="h-[3px] flex-1 rounded-full transition-colors duration-500"
              style={{
                background: position <= index ? 'var(--color-primary)' : 'rgb(var(--wx-tint) / 0.12)',
              }}
            />
          ))}
        </div>
      )}

      <div className="flex flex-1 flex-col justify-center py-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, y: -14 }}
            transition={{ duration: reduced ? 0.15 : 0.32, ease: [0.22, 1, 0.36, 1] }}
          >
            {body}
          </motion.div>
        </AnimatePresence>
      </div>

      <footer className="flex items-center justify-between gap-3">
        {index > 0 && step !== 'identity' ? (
          <button
            type="button"
            onClick={back}
            className="min-h-[40px] rounded-[var(--radius-pill)] px-3 text-xs text-muted transition hover:text-ink"
          >
            ← {t(language, 'onbBack')}
          </button>
        ) : (
          <span />
        )}
        {/* The reader can always leave. Onboarding that traps is onboarding
            that gets abandoned at the door. */}
        {step !== 'identity' && (
          <button
            type="button"
            onClick={finish}
            className="min-h-[40px] rounded-[var(--radius-pill)] px-3 text-xs text-faint transition hover:text-muted"
          >
            {t(language, 'onbContinueGuest')} →
          </button>
        )}
      </footer>
    </main>
  )
}
