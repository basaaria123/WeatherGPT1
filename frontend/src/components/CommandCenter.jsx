import { motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
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
          className="mt-3 rounded-[var(--radius-pill)] border border-white/15 bg-white/[0.06] px-3 py-1.5 text-xs text-ink"
        >
          {t(language, 'retry')}
        </button>
      </section>
    )
  }

  if (!data) return null

  const { current = {}, risk, location } = data
  const updated = relativeTime(data.generated_at)

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="glass glass-raised relative overflow-hidden p-5 sm:p-6"
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
          {t(language, 'commandCenter')}
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
            <p className="mt-1.5 text-sm font-medium text-ink-soft">{current.condition}</p>
          )}
          <p className="mt-0.5 truncate text-xs text-muted">
            {location?.name}
            {location?.admin1 && location.admin1 !== location.name ? `, ${location.admin1}` : ''}
            {updated ? ` · ${t(language, 'updated')} ${updated}` : ''}
          </p>
        </div>

        {risk?.detected_hazard && risk.detected_hazard !== 'None' && (
          <div className="ml-auto hidden text-right sm:block">
            <div className="text-[10px] uppercase tracking-[0.12em] text-faint">{t(language, 'hazard')}</div>
            <div className="text-sm font-semibold text-ink">{risk.detected_hazard}</div>
          </div>
        )}
      </div>

      <div className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3.5 border-t border-white/[0.07] pt-4 sm:grid-cols-3 lg:grid-cols-4">
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
