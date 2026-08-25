import { motion } from 'framer-motion'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { severityOf, isActionable } from './ui/severity'
import { EmptyState, LoadingBlock, Panel, Skeleton } from './ui/Primitives'
import WeatherGlyph from './ui/WeatherGlyph'

/**
 * Next 24 hours, horizontally scrollable on mobile.
 *
 * Risk-level highlighting comes from the backend timeline endpoint, which uses
 * the same engine as everything else — so a highlighted hour here is the same
 * hour that would fire an alert.
 */
export default function Timeline({ data, loading, error }) {
  const language = useStore((s) => s.language)

  if (loading && !data) {
    return (
      <Panel title={t(language, 'next24')}>
        <div className="flex gap-2 overflow-hidden">
          {Array.from({ length: 8 }).map((_, index) => (
            <Skeleton key={index} className="h-28 w-16 shrink-0" />
          ))}
        </div>
      </Panel>
    )
  }

  const hours = data?.hours ?? []
  if (error && !hours.length) {
    return (
      <Panel title={t(language, 'next24')}>
        <EmptyState icon="!" message={error} />
      </Panel>
    )
  }
  if (!hours.length) {
    return (
      <Panel title={t(language, 'next24')}>
        <LoadingBlock label={t(language, 'loading')} lines={2} />
      </Panel>
    )
  }

  const peak = hours.reduce((best, hour) => (hour.risk_score > best.risk_score ? hour : best), hours[0])

  return (
    <Panel
      title={t(language, 'next24')}
      action={
        isActionable(peak.risk_level) ? (
          <span className="text-[11px] text-muted">
            Peak {peak.risk_level.toLowerCase()} risk at {formatHour(peak.time)}
          </span>
        ) : null
      }
    >
      <div className="scroll-x -mx-1 flex min-w-0 gap-1.5 px-1 pb-1">
        {hours.map((hour, index) => (
          <HourCard key={hour.time} hour={hour} index={index} />
        ))}
      </div>
    </Panel>
  )
}

function HourCard({ hour, index }) {
  const tone = severityOf(hour.risk_level)
  const risky = isActionable(hour.risk_level)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.018, 0.4) }}
      title={`${formatHour(hour.time)} · ${hour.condition ?? ''} · ${hour.risk_level} risk (${hour.risk_score}/100)`}
      className="flex w-[4.4rem] shrink-0 flex-col items-center gap-1.5 rounded-xl border p-2 text-center"
      style={{
        borderColor: risky ? tone.ring : 'rgb(255 255 255 / 0.07)',
        background: risky ? tone.tint : 'rgb(255 255 255 / 0.03)',
      }}
    >
      <span className="text-[11px] font-medium text-muted">{formatHour(hour.time)}</span>
      <WeatherGlyph code={hour.weather_code} size={26} />
      <span className="text-sm font-semibold text-ink">
        {hour.temperature_c !== null && hour.temperature_c !== undefined
          ? `${Math.round(hour.temperature_c)}°`
          : '—'}
      </span>
      {hour.precipitation_probability_pct !== null && hour.precipitation_probability_pct !== undefined && (
        <span className="text-[11px] text-accent">{Math.round(hour.precipitation_probability_pct)}%</span>
      )}
      {/* Icon + colour together, so risk is not conveyed by colour alone. */}
      <span className="text-[10px] font-semibold" style={{ color: tone.color }}>
        <span aria-hidden="true">{tone.icon}</span> {hour.risk_score}
      </span>
    </motion.div>
  )
}

function formatHour(iso) {
  if (!iso) return '—'
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return String(iso).slice(11, 16)
  return parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
}
