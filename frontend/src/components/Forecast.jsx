import { motion } from 'framer-motion'
import { weekdayLabel } from '../i18n/datetime'
import { levelLabel, t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { severityOf } from './ui/severity'
import { EmptyState, Panel, Skeleton } from './ui/Primitives'
import WeatherGlyph from './ui/WeatherGlyph'
import Icon from './ui/Icon'

/** Seven-day strip. Today is highlighted; risk comes from the shared engine. */
export default function Forecast({ data, loading, error }) {
  const language = useStore((s) => s.language)

  if (loading && !data) {
    return (
      <Panel title={t(language, 'forecast7')}>
        <div className="space-y-2">
          {Array.from({ length: 7 }).map((_, index) => (
            <Skeleton key={index} className="h-10" />
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
      {/* A row per day rather than a row of cards.
          Seven cards side by side on a phone meant four visible, three off the
          edge, and each one narrow enough to hold a temperature and nothing
          else — so the page ran out of content a third of the way down while
          the forecast itself was cropped. A row is the width of the screen: it
          fits the high and the low, the chance of rain, how much, and the risk,
          and seven of them fill the page with forecast instead of with space. */}
      <ol className="min-w-0">
        {days.map((day, index) => {
          const tone = severityOf(day.risk_level)
          const isToday = index === 0
          return (
            <motion.li
              key={day.date}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.28, delay: index * 0.03 }}
              className={`grid min-w-0 grid-cols-[2.7rem_1.6rem_1fr_auto] items-center gap-2 border-b
                          border-[var(--wx-border)] py-2 last:border-b-0 ${
                            isToday ? 'rounded-[var(--radius-control)] bg-[rgb(var(--wx-tint)/0.05)] px-2' : ''
                          }`}
            >
              <span className={`truncate text-[12px] font-bold ${isToday ? 'text-primary' : 'text-ink-soft'}`}>
                {isToday ? t(language, 'today') : weekdayLabel(day.date, language)}
              </span>

              <span className="justify-self-center" title={day.condition ?? ''}>
                <WeatherGlyph code={day.weather_code} size={20} />
              </span>

              {/* High over low, then how likely, then how much. Tabular figures
                  so the column reads down as numbers rather than as ragged
                  text. */}
              <span className="flex min-w-0 items-baseline gap-2 tabular-nums">
                <span className="shrink-0 text-[13px] font-bold text-ink">
                  {day.temp_max_c != null ? `${Math.round(day.temp_max_c)}°` : '—'}
                  {day.temp_min_c != null && (
                    <span className="font-semibold text-faint"> / {Math.round(day.temp_min_c)}°</span>
                  )}
                </span>
                {day.precipitation_probability_pct != null && (
                  <span className="flex shrink-0 items-center gap-[2px] text-[11px] font-semibold text-primary">
                    <Icon name="droplet" size={10} />
                    {Math.round(day.precipitation_probability_pct)}%
                  </span>
                )}
                {day.precipitation_sum_mm > 0 && (
                  <span className="shrink-0 rounded-[var(--radius-pill)] bg-[rgb(var(--wx-tint)/0.07)] px-1.5
                                   py-px text-[10px] font-semibold text-muted">
                    {day.precipitation_sum_mm.toFixed(day.precipitation_sum_mm < 10 ? 1 : 0)} mm
                  </span>
                )}
              </span>

              {/* Risk as shape, colour and word — never colour alone. */}
              <span
                className="flex shrink-0 items-center gap-1 rounded-[var(--radius-pill)] px-1.5 py-[3px] text-[10px] font-bold"
                style={{ color: tone.ink, background: tone.tint }}
              >
                <span aria-hidden="true">{tone.icon}</span>
                <span className="hidden min-[360px]:inline">{levelLabel(language, day.risk_level)}</span>
              </span>
            </motion.li>
          )
        })}
      </ol>
    </Panel>
  )
}
