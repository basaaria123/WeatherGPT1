import { AnimatePresence, motion } from 'framer-motion'
import { useEffect } from 'react'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { SeverityPill } from './ui/Primitives'

/**
 * Side-by-side: an official-style bulletin against WeatherGPT's explanation.
 *
 * Both columns are rendered from the *same* backend response — the left is that
 * data formatted the way a technical bulletin states it, the right is the
 * assistant's plain-language answer. Nothing is scripted or simulated, so the
 * contrast on screen is the real contrast in the product. When the deployment
 * is serving fixture data, the header banner and the badge here say so.
 */

function bulletinLines(answer, current, location) {
  const source = answer?.raw_weather?.current ?? current ?? {}
  const next = answer?.raw_weather?.next_24_hours ?? {}
  const risk = answer?.risk

  const rows = [
    ['STATION', location?.name?.toUpperCase() ?? '—'],
    ['T2M', source.temperature_c, '°C'],
    ['APP.T', source.apparent_temperature_c, '°C'],
    ['RH', source.humidity_pct, '%'],
    ['PoP', source.precipitation_probability_pct, '%'],
    ['PRCP', source.precipitation_mm, 'mm'],
    ['PRCP/24H', next.precipitation_total_mm, 'mm'],
    ['FF10', source.wind_speed_kmh, 'km/h'],
    ['FX10', source.wind_gust_kmh, 'km/h'],
    ['MSLP', source.pressure_hpa, 'hPa'],
    ['WW', source.weather_code, ''],
  ]

  const lines = rows
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value, unit]) =>
      typeof value === 'number'
        ? `${key.padEnd(9)} ${value.toFixed(unit === 'mm' || unit === '°C' ? 1 : 0)}${unit}`
        : `${key.padEnd(9)} ${value}`,
    )

  if (risk) {
    lines.push(`${'HAZARD'.padEnd(9)} ${risk.detected_hazard.toUpperCase()}`)
    lines.push(`${'RISK'.padEnd(9)} ${risk.risk_score}/100 ${risk.risk_level.toUpperCase()}`)
  }
  return lines
}

export default function DemoMode({ answer }) {
  const language = useStore((s) => s.language)
  const open = useStore((s) => s.demoOpen)
  const setOpen = useStore((s) => s.setDemoOpen)
  const current = useStore((s) => s.current)
  const location = useStore((s) => s.location)
  const dataSource = useStore((s) => s.dataSource)

  useEffect(() => {
    if (!open) return undefined
    const onKey = (event) => event.key === 'Escape' && setOpen(false)
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, setOpen])

  const lines = bulletinLines(answer, current, location)

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={() => setOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label={t(language, 'demoTitle')}
          className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto
                     bg-[rgb(2_6_14/0.82)] p-4 backdrop-blur-md"
        >
          <motion.div
            initial={{ opacity: 0, y: 18, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            onClick={(event) => event.stopPropagation()}
            className="glass glass-raised my-auto w-full max-w-4xl p-5 sm:p-6"
          >
            <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-ink">{t(language, 'demoTitle')}</h2>
                <p className="mt-0.5 text-[11px] text-muted">
                  Both panels are rendered from the same backend response.
                </p>
              </div>
              <div className="flex items-center gap-2">
                {dataSource === 'fixture' ? (
                  <span className="rounded-[var(--radius-pill)] border border-caution/40 bg-caution/12 px-2 py-0.5
                                   text-[10px] font-bold tracking-wider text-caution">
                    {t(language, 'demoLabel')} · {t(language, 'simulated')}
                  </span>
                ) : (
                  <span className="rounded-[var(--radius-pill)] border border-safe/40 bg-safe/12 px-2 py-0.5
                                   text-[10px] font-bold tracking-wider text-safe">
                    {t(language, 'live')}
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  aria-label="Close"
                  className="grid h-8 w-8 place-items-center rounded-full border border-white/12
                             bg-white/[0.05] text-sm text-ink-soft transition hover:bg-white/[0.12]"
                >
                  ✕
                </button>
              </div>
            </header>

            <div className="grid gap-3 lg:grid-cols-[1fr_auto_1fr] lg:items-center">
              <motion.div
                initial={{ opacity: 0, x: -14 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.45, delay: 0.1 }}
                className="rounded-xl border border-white/[0.09] bg-black/35 p-4"
              >
                <h3 className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-faint">
                  {t(language, 'demoBulletin')}
                </h3>
                <pre className="scroll-x whitespace-pre font-mono text-[11px] leading-[1.7] text-muted">
                  {lines.length ? lines.join('\n') : 'Awaiting observations…'}
                </pre>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, scale: 0.6 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4, delay: 0.35 }}
                className="flex items-center justify-center"
                aria-hidden="true"
              >
                <motion.div
                  animate={{ x: [0, 5, 0] }}
                  transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
                  className="hidden items-center gap-1.5 lg:flex"
                >
                  <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-primary">
                    WeatherGPT
                  </span>
                  <span className="text-xl text-primary">→</span>
                </motion.div>
                <motion.span
                  animate={{ y: [0, 5, 0] }}
                  transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
                  className="text-xl text-primary lg:hidden"
                >
                  ↓
                </motion.span>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 14 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.45, delay: 0.55 }}
                className="rounded-xl border border-primary/25 bg-primary/[0.06] p-4"
              >
                <h3 className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
                  {t(language, 'demoPlain')}
                </h3>
                {answer ? (
                  <>
                    <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-ink">{answer.answer}</p>
                    {answer.actions?.length > 0 && (
                      <ul className="mt-3 space-y-1.5 border-t border-white/[0.09] pt-2.5">
                        {answer.actions.slice(0, 3).map((action, index) => (
                          <li key={index} className="flex gap-2 text-[12px] leading-relaxed text-ink-soft">
                            <span aria-hidden="true" className="mt-[3px] text-secondary">▸</span>
                            <span className="min-w-0">{action}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                    {answer.risk && (
                      <div className="mt-3">
                        <SeverityPill
                          level={answer.risk.risk_level}
                          score={`${answer.risk.risk_score}/100`}
                          compact
                        />
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-[13px] text-muted">
                    Ask WeatherGPT a question and its answer appears here beside the raw bulletin.
                  </p>
                )}
              </motion.div>
            </div>

            <p className="mt-4 text-[11px] leading-relaxed text-faint">{t(language, 'disclaimer')}</p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
