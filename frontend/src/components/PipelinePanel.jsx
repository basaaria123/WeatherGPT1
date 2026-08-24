import { AnimatePresence, motion } from 'framer-motion'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { EmptyState, Panel, SeverityPill } from './ui/Primitives'

/**
 * The signature view: raw data → WeatherGPT's reading → recommended action.
 *
 * Every stage is sourced, not narrated. The left column lists the exact numbers
 * the backend used, the middle is the backend's own explanation field, and the
 * right is its action list — so the visual claim ("we translate data into
 * action") is literally traceable on screen.
 */

const stageVariants = {
  hidden: { opacity: 0, y: 12 },
  show: (index) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, delay: index * 0.14, ease: [0.22, 1, 0.36, 1] },
  }),
}

function readings(raw, current) {
  const source = raw?.current ?? current ?? {}
  const next = raw?.next_24_hours ?? {}
  const rows = [
    { label: 'Temperature', value: source.temperature_c, unit: '°C' },
    { label: 'Feels like', value: source.apparent_temperature_c, unit: '°C' },
    { label: 'Humidity', value: source.humidity_pct, unit: '%' },
    { label: 'Rain chance', value: source.precipitation_probability_pct, unit: '%' },
    { label: 'Wind', value: source.wind_speed_kmh, unit: 'km/h' },
    { label: 'Gusts', value: source.wind_gust_kmh, unit: 'km/h' },
    { label: 'Rain next 24 h', value: next.precipitation_total_mm, unit: 'mm' },
    { label: 'Pressure', value: source.pressure_hpa, unit: 'hPa' },
  ]
  // Show only what the provider actually returned.
  return rows.filter((row) => row.value !== null && row.value !== undefined).slice(0, 6)
}

export default function PipelinePanel({ answer }) {
  const language = useStore((s) => s.language)
  const current = useStore((s) => s.current)

  if (!answer) {
    return (
      <Panel title={t(language, 'pipeline')}>
        <EmptyState
          icon="◵"
          message="Ask a question and this panel will show the measurements behind the answer, and what to do about them."
        />
      </Panel>
    )
  }

  const rows = readings(answer.raw_weather, current)
  const stages = [
    {
      key: 'data',
      label: t(language, 'stageData'),
      icon: '◵',
      accent: 'var(--color-accent)',
      body: (
        <dl className="space-y-1.5">
          {rows.map((row) => (
            <div key={row.label} className="flex items-baseline justify-between gap-2">
              <dt className="truncate text-[11px] text-faint">{row.label}</dt>
              <dd className="shrink-0 font-mono text-[12px] font-semibold text-ink">
                {typeof row.value === 'number' ? row.value.toFixed(row.unit === 'mm' || row.unit === '°C' ? 1 : 0) : row.value}
                <span className="ml-0.5 text-[10px] font-normal text-muted">{row.unit}</span>
              </dd>
            </div>
          ))}
        </dl>
      ),
    },
    {
      key: 'understanding',
      label: t(language, 'stageUnderstanding'),
      icon: '◈',
      accent: 'var(--color-primary)',
      body: (
        <>
          <p className="text-[13px] leading-relaxed text-ink-soft">
            {answer.explanation || answer.answer}
          </p>
          {answer.risk && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <SeverityPill level={answer.risk.risk_level} score={`${answer.risk.risk_score}/100`} compact />
              {answer.risk.detected_hazard !== 'None' && (
                <span className="text-[11px] text-muted">{answer.risk.detected_hazard}</span>
              )}
            </div>
          )}
        </>
      ),
    },
    {
      key: 'action',
      label: t(language, 'stageAction'),
      icon: '➜',
      accent: answer.action_mode ? 'var(--color-warning)' : 'var(--color-secondary)',
      body:
        answer.actions?.length > 0 ? (
          <ul className="space-y-2">
            {answer.actions.slice(0, 4).map((action, index) => (
              <li key={index} className="flex gap-2 text-[13px] leading-relaxed text-ink-soft">
                <span aria-hidden="true" className="mt-[3px] shrink-0 text-secondary">▸</span>
                <span className="min-w-0">{action}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[13px] leading-relaxed text-muted">
            No special precautions are needed right now.
          </p>
        ),
    },
  ]

  return (
    <Panel title={t(language, 'pipeline')}>
      <AnimatePresence mode="wait">
        <motion.div
          key={answer.id}
          className="grid gap-2.5 lg:grid-cols-[1fr_auto_1fr_auto_1fr] lg:items-stretch"
        >
          {stages.map((stage, index) => (
            <motion.div key={stage.key} className="contents">
              <motion.article
                variants={stageVariants}
                initial="hidden"
                animate="show"
                custom={index}
                className="min-w-0 rounded-xl border border-white/[0.08] bg-white/[0.03] p-3.5"
              >
                <header className="mb-2.5 flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className="grid h-6 w-6 place-items-center rounded-md text-[11px]"
                    style={{ background: `color-mix(in srgb, ${stage.accent} 14%, transparent)`, color: stage.accent }}
                  >
                    {stage.icon}
                  </span>
                  <h3 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted">
                    {stage.label}
                  </h3>
                </header>
                {stage.body}
              </motion.article>

              {index < stages.length - 1 && (
                <motion.div
                  variants={stageVariants}
                  initial="hidden"
                  animate="show"
                  custom={index + 0.5}
                  className="flex items-center justify-center py-1 lg:py-0"
                  aria-hidden="true"
                >
                  <Arrow />
                </motion.div>
              )}
            </motion.div>
          ))}
        </motion.div>
      </AnimatePresence>
    </Panel>
  )
}

function Arrow() {
  return (
    <>
      {/* Horizontal on wide layouts, vertical when the stages stack. */}
      <motion.svg
        width="26"
        height="12"
        viewBox="0 0 26 12"
        fill="none"
        className="hidden lg:block"
        animate={{ x: [0, 3, 0] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
      >
        <path d="M0 6h20M16 2l5 4-5 4" stroke="var(--color-primary)" strokeWidth="1.5" strokeOpacity="0.65" strokeLinecap="round" strokeLinejoin="round" />
      </motion.svg>
      <motion.svg
        width="12"
        height="22"
        viewBox="0 0 12 22"
        fill="none"
        className="lg:hidden"
        animate={{ y: [0, 3, 0] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
      >
        <path d="M6 0v16M2 12l4 5 4-5" stroke="var(--color-primary)" strokeWidth="1.5" strokeOpacity="0.65" strokeLinecap="round" strokeLinejoin="round" />
      </motion.svg>
    </>
  )
}
