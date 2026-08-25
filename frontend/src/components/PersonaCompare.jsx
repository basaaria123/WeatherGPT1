import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { hazardLabel, profileLabel, t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { severityOf } from './ui/severity'

/**
 * One weather fact, five decisions.
 *
 * The shared condition is stated once at the top; below it the same risk output
 * fans out into different guidance per persona. This is the clearest statement
 * of what the product does — a single forecast is not a single decision.
 *
 * Everything shown comes from /advisory/personas, which reads the same risk
 * engine as the rest of the dashboard.
 */
const ICONS = { farmer: '🌾', fisherman: '🎣', traveler: '🧳', commuter: '🚌', general: '🏠' }

export default function PersonaCompare({ open, onClose, location }) {
  const language = useStore((s) => s.language)
  const userType = useStore((s) => s.userType)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!open || !location) return undefined
    let cancelled = false
    setData(null)
    setError(null)
    api
      .advisoryPersonas({ location, language })
      .then((payload) => !cancelled && setData(payload))
      .catch((err) => !cancelled && setError(err.message))
    return () => { cancelled = true }
  }, [open, location, language])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (event) => event.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-[var(--wx-overlay)] p-3 py-[6vh] backdrop-blur-sm"
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-label={t(language, 'sameWeather')}
        >
          <motion.div
            initial={{ opacity: 0, y: -12, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
            onClick={(event) => event.stopPropagation()}
            className="glass glass-raised w-full max-w-5xl p-4 sm:p-5"
          >
            <div className="mb-3 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-base font-semibold text-ink">{t(language, 'sameWeather')}</h2>
                {data?.location?.name && (
                  <p className="text-[11px] text-muted">{data.location.name}</p>
                )}
              </div>
              <button
                type="button"
                onClick={onClose}
                className="shrink-0 rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.14)]
                           px-3 py-1.5 text-[11px] text-ink-soft transition hover:border-[rgb(var(--wx-tint)/0.3)]"
              >
                {t(language, 'closeCompare')} ✕
              </button>
            </div>

            {error && <p className="text-xs text-danger">{error}</p>}
            {!data && !error && <p className="text-xs text-muted">{t(language, 'loading')}</p>}

            {data && (() => {
              // Actions every persona shares are hazard safety, not a decision
              // that differs by role. Repeating them in all five columns buries
              // the one line that actually differs, so they are lifted out and
              // stated once beneath.
              const lists = data.personas.map((p) => p.actions.map((a) => a.action))
              const shared = lists.length
                ? lists[0].filter((action) => lists.every((list) => list.includes(action)))
                : []
              return (
              <>
                {/* The fact everyone shares, stated once, above the divergence. */}
                <div className="mb-3 rounded-xl border border-[rgb(var(--wx-tint)/0.1)] bg-[rgb(var(--wx-tint)/0.04)] p-3">
                  <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
                    {t(language, 'sharedCondition')}
                  </p>
                  <p className="text-[13px] leading-relaxed text-ink-soft">{data.shared_condition}</p>
                  {data.risk && (
                    <p className="mt-1.5 flex items-center gap-1.5 text-[12px]">
                      <span aria-hidden="true" style={{ color: severityOf(data.risk.risk_level).color }}>
                        {severityOf(data.risk.risk_level).icon}
                      </span>
                      <span className="font-semibold text-ink">
                        {hazardLabel(language, data.risk.detected_hazard)}
                      </span>
                      <span className="text-muted">
                        · {data.risk.risk_level} {data.risk.risk_score}/100
                      </span>
                    </p>
                  )}
                </div>

                {/* Horizontally scrollable on a phone, gridded on a laptop. */}
                <div className="scroll-x -mx-1 flex gap-2.5 px-1 pb-1 sm:mx-0 sm:grid sm:grid-cols-2 sm:px-0 lg:grid-cols-5">
                  {data.personas.map((persona, index) => {
                    const mine = persona.user_type === userType
                    return (
                      <motion.article
                        key={persona.user_type}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3, delay: index * 0.07 }}
                        className="w-[16rem] shrink-0 rounded-xl border p-3 sm:w-auto"
                        style={{
                          borderColor: mine ? 'var(--color-primary)' : 'rgb(var(--wx-tint) / 0.1)',
                          background: mine ? 'rgb(var(--wx-tint) / 0.07)' : 'rgb(var(--wx-tint) / 0.03)',
                        }}
                      >
                        <div className="mb-2 flex items-center gap-1.5">
                          <span aria-hidden="true">{ICONS[persona.user_type] ?? '◆'}</span>
                          <h3 className="text-[12px] font-semibold text-ink">
                            {profileLabel(language, persona.user_type)}
                          </h3>
                          {mine && (
                            <span className="ml-auto rounded-[var(--radius-pill)] border border-primary/40
                                             bg-primary/10 px-1.5 py-px text-[10px] font-semibold text-primary">
                              {t(language, 'forYou')}
                            </span>
                          )}
                        </div>
                        <ul className="space-y-1.5">
                          {persona.actions
                            .filter((item) => !shared.includes(item.action))
                            .map((item, i) => (
                              <li key={i} className="text-[11px] leading-relaxed text-ink">
                                <span className="min-w-0">{item.action}</span>
                                {item.reason && (
                                  <span className="mt-0.5 block text-[10px] text-muted">{item.reason}</span>
                                )}
                              </li>
                            ))}
                        </ul>
                      </motion.article>
                    )
                  })}
                </div>

                {shared.length > 0 && (
                  <div className="mt-3 rounded-xl border border-[rgb(var(--wx-tint)/0.1)] bg-[rgb(var(--wx-tint)/0.03)] p-3">
                    <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
                      {t(language, 'everyoneShould')}
                    </p>
                    <ul className="grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
                      {shared.map((action, i) => (
                        <li key={i} className="flex gap-1.5 text-[11px] leading-relaxed text-ink-soft">
                          <span aria-hidden="true" className="text-muted">·</span>
                          <span className="min-w-0">{action}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {data.disclaimer && (
                  <p className="mt-3 text-[11px] leading-relaxed text-faint">{data.disclaimer}</p>
                )}
              </>
              )
            })()}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
