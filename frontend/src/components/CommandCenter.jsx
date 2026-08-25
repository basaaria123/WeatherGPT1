import { motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { hazardLabel, t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { severityOf } from './ui/severity'
import { LoadingBlock, Metric, SeverityPill } from './ui/Primitives'
import WeatherGlyph from './ui/WeatherGlyph'

/**
 * Hero conditions card.
 *
 * Only renders metrics the API actually returned — a missing field is omitted
 * entirely rather than shown as "N/A", which is why every Metric is guarded
 * rather than defaulted.
 */

function AnimatedNumber({ value, decimals = 0 }) {
  const [display, setDisplay] = useState(value)
  const frame = useRef(null)
  const from = useRef(value)

  useEffect(() => {
    if (value === null || value === undefined) return undefined
    const start = performance.now()
    const origin = from.current ?? value
    const delta = value - origin
    const duration = 550

    const step = (now) => {
      const progress = Math.min(1, (now - start) / duration)
      // easeOutCubic — settles rather than snapping.
      const eased = 1 - (1 - progress) ** 3
      setDisplay(origin + delta * eased)
      if (progress < 1) frame.current = requestAnimationFrame(step)
      else from.current = value
    }
    frame.current = requestAnimationFrame(step)
    return () => frame.current && cancelAnimationFrame(frame.current)
  }, [value])

  if (value === null || value === undefined) return null
  return <>{Number(display).toFixed(decimals)}</>
}

function relativeTime(iso) {
  if (!iso) return null
  const then = new Date(iso)
  if (Number.isNaN(then.getTime())) return null
  const minutes = Math.max(0, Math.round((Date.now() - then.getTime()) / 60000))
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  return `${hours} h ago`
}

export default function CommandCenter({ data, loading, error, onRetry }) {
  const language = useStore((s) => s.language)

  if (loading && !data) {
    return (
      <section className="glass p-5">
        <LoadingBlock label={t(language, 'loading')} lines={4} />
      </section>
    )
  }

  if (error && !data) {
    return (
      <section className="glass p-5">
        <p className="text-sm font-semibold text-ink">{t(language, 'errorTitle')}</p>
        <p className="mt-1 text-xs text-muted">{error}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.15)] bg-[rgb(var(--wx-tint)/0.06)] px-3 py-1.5 text-xs text-ink"
        >
          {t(language, 'retry')}
        </button>
      </section>
    )
  }

  if (!data) return null

  const { current = {}, risk, location } = data
  const updated = relativeTime(data.generated_at)
  const officialCount = data.official_alert_count ?? 0

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="glass glass-raised glass-hero relative overflow-hidden p-5 sm:p-6"
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <h2 className="text-[12px] font-semibold uppercase tracking-[0.14em] text-muted">
          {t(language, 'conditionsNow')}
        </h2>
        {risk && <SeverityPill level={risk.risk_level} score={`${risk.risk_score}/100`} />}
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-4">
        <WeatherGlyph code={current.weather_code} size={76} className="shrink-0" />

        <div className="min-w-0">
          {current.temperature_c !== null && current.temperature_c !== undefined && (
            <div className="flex items-start gap-1 text-[3.4rem] font-semibold leading-none tracking-tight sm:text-6xl">
              <AnimatedNumber value={current.temperature_c} decimals={0} />
              <span className="mt-1.5 text-2xl text-muted">°C</span>
            </div>
          )}
          {current.condition && (
            <p className="mt-1.5 text-[15px] font-medium text-ink-soft">{current.condition}</p>
          )}
          <p className="mt-0.5 truncate text-[12px] text-muted">
            {location?.name}
            {location?.admin1 && location.admin1 !== location.name ? `, ${location.admin1}` : ''}
            {updated ? ` · ${t(language, 'updated')} ${updated}` : ''}
          </p>
        </div>

        {risk && <RiskExplainer risk={risk} language={language} />}
      </div>

      {/* A detected hazard and an issued warning are different claims, so they
          are shown as two separate statements rather than one badge. */}
      {risk && <HazardVsAlerts risk={risk} officialCount={officialCount} language={language} />}

      <div className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3.5 border-t border-[rgb(var(--wx-tint)/0.07)] pt-4 sm:grid-cols-3 lg:grid-cols-4">
        <Metric
          label={t(language, 'feelsLike')}
          value={current.apparent_temperature_c?.toFixed?.(0)}
          unit="°C"
        />
        <Metric label={t(language, 'humidity')} value={current.humidity_pct?.toFixed?.(0)} unit="%" />
        <Metric label={t(language, 'wind')} value={current.wind_speed_kmh?.toFixed?.(0)} unit="km/h" />
        <Metric label={t(language, 'gusts')} value={current.wind_gust_kmh?.toFixed?.(0)} unit="km/h" />
        <Metric
          label={t(language, 'rainChance')}
          value={current.precipitation_probability_pct?.toFixed?.(0)}
          unit="%"
        />
        <Metric label={t(language, 'precipitation')} value={current.precipitation_mm?.toFixed?.(1)} unit="mm" />
        <Metric label={t(language, 'pressure')} value={current.pressure_hpa?.toFixed?.(0)} unit="hPa" />
        <Metric label={t(language, 'cloud')} value={current.cloud_cover_pct?.toFixed?.(0)} unit="%" />
        <Metric label={t(language, 'visibility')} value={current.visibility_km?.toFixed?.(1)} unit="km" />
      </div>
    </motion.section>
  )
}


/**
 * Risk score with its reasoning attached.
 *
 * Both the drivers and the per-hazard bars come straight from the risk engine's
 * own output — the engine names the values it scored, so nothing here is a
 * reconstruction of how the number was reached.
 */
function RiskExplainer({ risk, language }) {
  const [open, setOpen] = useState(false)
  const tone = severityOf(risk.risk_level)

  const contributors = Object.entries(risk.hazard_scores ?? {})
    .filter(([, score]) => score >= 1)
    .sort((a, b) => b[1] - a[1])

  return (
    <div className="ml-auto w-full sm:w-auto sm:min-w-[13rem] sm:text-right">
      <div className="text-[11px] uppercase tracking-[0.12em] text-faint">{t(language, 'riskScore')}</div>
      <div className="flex items-baseline gap-1.5 sm:justify-end">
        <span className="text-2xl font-semibold" style={{ color: tone.color }}>
          {risk.risk_score}
        </span>
        <span className="text-[13px] text-muted">/100</span>
      </div>
      <p className="mt-1 text-[11px] leading-relaxed text-faint sm:max-w-[15rem]">
        {t(language, 'riskBasis')}
      </p>

      {(contributors.length > 0 || risk.drivers?.length > 0) && (
        <>
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            className="mt-1.5 text-[11px] text-muted underline underline-offset-2 transition hover:text-ink"
          >
            {t(language, 'whyThisScore')} {open ? '▴' : '▾'}
          </button>

          {open && (
            <div className="mt-2 rounded-xl border border-[rgb(var(--wx-tint)/0.09)] bg-black/15 p-2.5 text-left">
              {risk.drivers?.length > 0 && (
                <ul className="mb-2 space-y-1">
                  {risk.drivers.map((driver, index) => (
                    <li key={index} className="flex gap-1.5 text-[11px] leading-relaxed text-ink-soft">
                      <span aria-hidden="true" style={{ color: tone.color }}>▸</span>
                      <span className="min-w-0">{driver}</span>
                    </li>
                  ))}
                </ul>
              )}

              {contributors.length > 0 && (
                <>
                  <p className="mb-1.5 text-[11px] uppercase tracking-[0.12em] text-faint">
                    {t(language, 'riskFactors')}
                  </p>
                  <ul className="space-y-1.5">
                    {contributors.map(([hazard, score]) => (
                      <li key={hazard} className="flex items-center gap-2">
                        <span className="w-[7.5rem] shrink-0 truncate text-[11px] text-muted">
                          {hazardLabel(language, hazard)}
                        </span>
                        <span className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-[rgb(var(--wx-tint)/0.07)]">
                          <span
                            className="block h-full rounded-full"
                            style={{ width: `${score}%`, background: severityOf(levelFor(score)).color }}
                          />
                        </span>
                        <span className="w-6 shrink-0 text-right text-[11px] tabular-nums text-ink-soft">
                          {score}
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

/** Mirrors the engine's bands so a bar is coloured like the score it shows. */
function levelFor(score) {
  if (score <= 30) return 'Low'
  if (score <= 60) return 'Moderate'
  if (score <= 80) return 'High'
  return 'Severe'
}

/**
 * Two separate statements, never one.
 *
 * "Lightning risk detected" and "no official warning issued" are both true at
 * once far more often than not, and collapsing them into a single badge is what
 * made the old card read as self-contradictory.
 */
function HazardVsAlerts({ risk, officialCount, language }) {
  const tone = severityOf(risk.risk_level)
  const hasHazard = risk.detected_hazard && risk.detected_hazard !== 'None'

  return (
    <div className="mt-4 grid gap-2 border-t border-[rgb(var(--wx-tint)/0.07)] pt-3.5 sm:grid-cols-2">
      <div>
        <div className="text-[11px] uppercase tracking-[0.12em] text-faint">
          {t(language, 'hazardRisk')}
        </div>
        <div className="mt-0.5 flex items-center gap-1.5">
          {hasHazard && (
            <span aria-hidden="true" style={{ color: tone.color }}>{tone.icon}</span>
          )}
          <span className="text-[13px] font-semibold text-ink">
            {hasHazard ? hazardLabel(language, risk.detected_hazard) : t(language, 'noHazard')}
          </span>
        </div>
        {/* Only worth saying while no warning exists. Once one is issued the
            note would contradict the panel beside it. */}
        {hasHazard && officialCount === 0 && (
          <p className="mt-0.5 text-[11px] leading-relaxed text-faint">
            {t(language, 'hazardDetectedNote')}
          </p>
        )}
      </div>

      <div>
        <div className="text-[11px] uppercase tracking-[0.12em] text-faint">
          {t(language, 'officialAlerts')}
        </div>
        <div className="mt-0.5 flex items-center gap-1.5">
          <span aria-hidden="true" className={officialCount > 0 ? '' : 'text-safe'}>
            {officialCount > 0 ? '◆' : '✓'}
          </span>
          <span className="text-[13px] font-semibold text-ink">
            {officialCount === 0
              ? t(language, 'noOfficialAlerts')
              : officialCount === 1
                ? t(language, 'warningOne')
                : t(language, 'warningMany').replace('{n}', String(officialCount))}
          </span>
        </div>
      </div>
    </div>
  )
}
