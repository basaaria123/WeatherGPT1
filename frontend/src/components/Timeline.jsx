import { motion } from 'framer-motion'
import { levelLabel, t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { severityOf, isActionable } from './ui/severity'
import { EmptyState, LoadingBlock, Panel, Skeleton } from './ui/Primitives'
import WeatherGlyph from './ui/WeatherGlyph'
import Icon from './ui/Icon'

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
            {t(language, 'peakRisk')
              .replace('{level}', levelLabel(language, peak.risk_level))
              .replace('{time}', formatHour(peak.time))}
          </span>
        ) : null
      }
    >
      <div className="scroll-x -mx-1 flex min-w-0 gap-0.5 px-1 pb-1">
        {hours.map((hour, index) => (
          <HourCard key={hour.time} hour={hour} index={index} isNow={index === 0} language={language} />
        ))}
      </div>
    </Panel>
  )
}

function HourCard({ hour, index, isNow, language }) {
  const tone = severityOf(hour.risk_level)
  const risky = isActionable(hour.risk_level)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.018, 0.4) }}
      title={`${formatHour(hour.time)} · ${hour.condition ?? ''} · ${levelLabel(language, hour.risk_level)} (${hour.risk_score}/100)`}
      /* No border and no fill — the reference's hour strip is a column of
         readings on the card's own surface, and eight bordered boxes in a row
         read as eight cards rather than as one forecast.

         Risk is marked by a rule under the column rather than by a wash behind
         it. On a day the engine calls High from end to end — which is the day
         this strip matters most — a tint on every hour filled the whole strip
         orange and stopped distinguishing anything. */
      className="relative flex w-[3.9rem] shrink-0 flex-col items-center gap-1 rounded-[var(--radius-control)] px-1 pb-2.5 pt-2 text-center"
    >
      {/* The strip always starts at the current hour, so the first card says so
          rather than leaving the reader to infer it from the clock. */}
      <span className={`text-[10.5px] ${isNow ? 'font-bold text-primary' : 'font-medium text-muted'}`}>
        {isNow ? t(language, 'nowLabel') : formatHour(hour.time)}
      </span>

      <WeatherGlyph code={hour.weather_code} size={24} />

      <span className="text-[14px] font-bold tracking-[-0.01em] text-ink">
        {hour.temperature_c !== null && hour.temperature_c !== undefined
          ? `${Math.round(hour.temperature_c)}°`
          : '—'}
      </span>

      {hour.precipitation_probability_pct !== null && hour.precipitation_probability_pct !== undefined && (
        <span className="flex items-center gap-[2px] text-[10px] font-semibold text-primary">
          <Icon name="droplet" size={9} />
          {Math.round(hour.precipitation_probability_pct)}%
        </span>
      )}

      {hour.wind_speed_kmh !== null && hour.wind_speed_kmh !== undefined && (
        <span className="text-[9.5px] text-faint">{Math.round(hour.wind_speed_kmh)} km/h</span>
      )}

      {/* Icon + colour together, so risk is not conveyed by colour alone. Shown
          only once the engine calls the hour actionable: a "● 8" under every
          calm hour is nine-tenths of the strip spent saying nothing. */}
      {risky && (
        <>
          <span className="text-[9.5px] font-bold" style={{ color: tone.ink }}>
            <span aria-hidden="true">{tone.icon}</span> {hour.risk_score}
          </span>
          <span
            aria-hidden="true"
            className="absolute inset-x-1.5 bottom-0 h-[2.5px] rounded-full"
            style={{ background: tone.color }}
          />
        </>
      )}
    </motion.div>
  )
}

function formatHour(iso) {
  if (!iso) return '—'
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return String(iso).slice(11, 16)
  return parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
}
