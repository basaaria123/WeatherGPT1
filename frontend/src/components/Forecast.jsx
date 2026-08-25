import { motion } from 'framer-motion'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { severityOf } from './ui/severity'
import { EmptyState, Panel, Skeleton } from './ui/Primitives'
import WeatherGlyph from './ui/WeatherGlyph'

/** Seven-day strip. Today is highlighted; risk comes from the shared engine. */
export default function Forecast({ data, loading, error }) {
  const language = useStore((s) => s.language)

  if (loading && !data) {
    return (
      <Panel title={t(language, 'forecast7')}>
        <div className="grid grid-cols-4 gap-2 sm:grid-cols-7">
          {Array.from({ length: 7 }).map((_, index) => (
            <Skeleton key={index} className="h-24" />
          ))}
        </div>
      </Panel>
    )
  }

  const days = data?.days ?? []
  if (!days.length) {
    return (
      <Panel title={t(language, 'forecast7')}>
        <EmptyState icon="!" message={error ?? t(language, 'loading')} />
      </Panel>
    )
  }

  return (
    <Panel title={t(language, 'forecast7')}>
      <div className="scroll-x -mx-1 flex min-w-0 gap-1.5 px-1 pb-1 sm:grid sm:grid-cols-7 sm:gap-2 sm:overflow-visible">
        {days.map((day, index) => {
          const tone = severityOf(day.risk_level)
          const isToday = index === 0
          return (
            <motion.div
              key={day.date}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.04 }}
              title={`${day.condition ?? ''} · ${day.risk_level} risk`}
              className={`flex w-[4.6rem] shrink-0 flex-col items-center gap-1 rounded-xl border p-2 text-center sm:w-auto ${
                isToday ? 'border-primary/45 bg-primary/[0.08]' : 'border-[rgb(var(--wx-tint)/0.07)] bg-[rgb(var(--wx-tint)/0.03)]'
              }`}
            >
              <span className={`text-[11px] font-semibold ${isToday ? 'text-primary' : 'text-muted'}`}>
                {isToday ? 'Today' : dayLabel(day.date)}
              </span>
              <WeatherGlyph code={day.weather_code} size={26} />
              <span className="text-sm font-semibold text-ink">
                {day.temp_max_c !== null && day.temp_max_c !== undefined ? `${Math.round(day.temp_max_c)}°` : '—'}
              </span>
              {day.temp_min_c !== null && day.temp_min_c !== undefined && (
                <span className="text-[11px] text-faint">{Math.round(day.temp_min_c)}°</span>
              )}
              {day.precipitation_sum_mm > 0 && (
                <span className="text-[11px] text-accent">{day.precipitation_sum_mm.toFixed(0)}mm</span>
              )}
              <span className="text-[10px]" style={{ color: tone.color }} aria-label={`${day.risk_level} risk`}>
                <span aria-hidden="true">{tone.icon}</span>
              </span>
            </motion.div>
          )
        })}
      </div>
    </Panel>
  )
}

function dayLabel(iso) {
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return iso?.slice(5) ?? '—'
  return parsed.toLocaleDateString([], { weekday: 'short' })
}
