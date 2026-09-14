import { useCallback, useEffect, useState } from 'react'
import { api } from '../../api/client'
import { userMessage } from '../../api/errors'
import { t } from '../../i18n/ui'
import { useStore } from '../../store/useStore'
import Icon from '../ui/Icon'
import { LoadingBlock, Panel, Tabs } from '../ui/Primitives'
import TrendChart from './TrendChart'

/**
 * Historical & Climate Insights.
 *
 * Every number on this screen is measured. The series comes from
 * `/climate/history`, which aggregates Open-Meteo's historical archive — the
 * same provider the dashboard's forecast comes from — and nothing here
 * computes, smooths or estimates a value the archive did not return.
 *
 * That constraint is the whole design of the empty states. A climate screen
 * that fills its gaps looks finished and is worthless; this one says which of
 * three things went wrong and keeps every control working, so the selectors,
 * the chart frame and the hand-off to the assistant are all still there to be
 * demonstrated:
 *
 *   archive_unavailable  the provider could not be reached
 *   not_enough_years     fewer than two complete years in the window
 *   no_daily_series      the daily archive does not carry this measurement
 *
 * The third is permanent and worth stating plainly: Open-Meteo's daily archive
 * has temperature and precipitation and no relative humidity. Humidity is
 * offered because a reader will look for it, and it answers honestly rather
 * than being quietly derived from something that is not humidity.
 */

const PERIODS = [
  { id: 1, key: 'period1' },
  { id: 5, key: 'period5' },
  { id: 10, key: 'period10' },
  { id: 'custom', key: 'periodCustom' },
]

const PARAMETERS = [
  { id: 'temperature', key: 'paramTemperature' },
  { id: 'rainfall', key: 'paramRainfall' },
  { id: 'humidity', key: 'paramHumidity' },
]

const THIS_YEAR = new Date().getFullYear()

export default function ClimateInsights({ onBack, onAsk, onOpenLocation }) {
  const language = useStore((s) => s.language)
  const location = useStore((s) => s.location)
  const dataSource = useStore((s) => s.dataSource)

  const [period, setPeriod] = useState(5)
  const [parameter, setParameter] = useState('temperature')
  // Only consulted when `period === 'custom'`. Held here rather than in the
  // store because it is a view setting, not a preference.
  const [customFrom, setCustomFrom] = useState(THIS_YEAR - 10)
  const [customTo, setCustomTo] = useState(THIS_YEAR - 1)

  const [series, setSeries] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const years =
    period === 'custom' ? Math.max(2, Math.min(30, customTo - customFrom + 1)) : Number(period)

  const load = useCallback(async () => {
    if (!location?.name) return
    setLoading(true)
    setError(null)
    try {
      const data = await api.climateHistory({ location: location.name, parameter, years })
      setSeries(data)
    } catch (err) {
      setError(userMessage(err, language))
      setSeries(null)
    } finally {
      setLoading(false)
    }
  }, [location?.name, parameter, years, language])

  useEffect(() => { load() }, [load])

  const available = Boolean(series?.available)
  const summary = series?.summary ?? {}
  const trend = series?.trend ?? {}
  const decimals = series?.unit === 'mm' ? 0 : 1
  const show = (value) =>
    typeof value === 'number' ? `${value.toFixed(decimals)}${series?.unit ?? ''}` : '—'

  return (
    <>
      {/* --- Title -------------------------------------------------------- */}
      <section className="min-w-0 px-1 pt-0.5">
        <div className="flex min-w-0 items-start gap-2">
          <button
            type="button"
            onClick={onBack}
            aria-label={t(language, 'backToForecast')}
            className="-ml-1 mt-px grid h-7 w-7 shrink-0 place-items-center rounded-full text-ink-soft
                       transition hover:bg-[rgb(var(--wx-tint)/0.08)]"
          >
            <Icon name="chevronLeft" size={18} />
          </button>
          <div className="min-w-0">
            <h1 className="text-[16px] font-bold leading-tight tracking-[-0.015em] text-ink">
              {t(language, 'climateTitle')}
            </h1>
            <p className="mt-0.5 text-[11.5px] leading-[1.4] text-muted">
              {t(language, 'climateSubtitle')}
            </p>
          </div>
        </div>
      </section>

      {/* --- Location. The app's own picker, not a second one. ------------ */}
      <button
        type="button"
        onClick={onOpenLocation}
        className="glass flex w-full min-w-0 items-center gap-2 p-3 text-left transition
                   hover:border-primary/40"
      >
        <Icon name="pin" size={15} className="shrink-0 text-primary" />
        <span className="min-w-0 flex-1 truncate text-[13px] font-bold text-ink">
          {location?.name ?? '—'}
          {location?.admin1 && location.admin1 !== location.name && (
            <span className="font-medium text-muted">, {location.admin1}</span>
          )}
        </span>
        <span className="shrink-0 text-[11px] font-semibold text-primary">
          {t(language, 'changeLocation')}
        </span>
      </button>

      {/* --- Period ------------------------------------------------------- */}
      <Panel title={t(language, 'timePeriod')}>
        <Tabs
          idPrefix="climate-period"
          ariaLabel={t(language, 'timePeriod')}
          value={period}
          onChange={setPeriod}
          items={PERIODS.map((item) => ({ id: item.id, label: t(language, item.key) }))}
        />

        {period === 'custom' && (
          <div className="mt-3 flex min-w-0 items-end gap-2">
            <YearField
              label={t(language, 'fromYear')}
              value={customFrom}
              min={1960}
              max={customTo - 1}
              onChange={setCustomFrom}
            />
            <YearField
              label={t(language, 'toYear')}
              value={customTo}
              min={customFrom + 1}
              max={THIS_YEAR - 1}
              onChange={setCustomTo}
            />
          </div>
        )}
      </Panel>

      {/* --- Parameter ---------------------------------------------------- */}
      <Panel title={t(language, 'parameter')}>
        <div className="flex min-w-0 gap-1.5">
          {PARAMETERS.map((item) => {
            const active = parameter === item.id
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setParameter(item.id)}
                aria-pressed={active}
                /* No icon. Three pills across 350px with an icon each left
                   "Tempera…" — and a thermometer beside a truncated word is
                   less legible than the whole word. */
                className={`wx-pill min-w-0 flex-1 justify-center gap-0 px-1.5 py-[7px] text-[11.5px]
                            ${active ? 'wx-pill-on' : 'wx-pill-off'}`}
              >
                <span className="min-w-0 truncate">{t(language, item.key)}</span>
              </button>
            )
          })}
        </div>
      </Panel>

      {/* --- The trend ---------------------------------------------------- */}
      <Panel
        title={t(language, 'historicalTrend')}
        action={
          available && trend.direction && trend.direction !== 'unknown' ? (
            <TrendBadge direction={trend.direction} change={trend.change} unit={series.unit} />
          ) : null
        }
      >
        {loading && !series ? (
          <LoadingBlock label={t(language, 'loading')} lines={4} />
        ) : (
          <>
            <TrendChart
              points={available ? series.points : null}
              unit={series?.unit ?? ''}
              // A sum is a ratio quantity and starts at zero; a mean gets a
              // padded window, or fractions of a degree are an invisible line.
              // See the note in TrendChart.
              zeroBaseline={series?.parameter === 'rainfall'}
              label={
                available
                  ? `${t(language, `param${cap(series.parameter)}`)} · ${series.start_year}–${series.end_year}`
                  : ''
              }
              emptyLabel={error ?? noteText(language, series?.note)}
            />

            {available && (
              <p className="mt-2 text-[10.5px] leading-[1.45] text-faint">
                {t(language, 'climateSourceNote')}
                {dataSource === 'fixture' && (
                  <span className="font-semibold text-caution-ink"> · {t(language, 'simulated')}</span>
                )}
              </p>
            )}
          </>
        )}
      </Panel>

      {/* --- Average / highest / lowest ------------------------------------ */}
      <div className="grid min-w-0 grid-cols-3 gap-2">
        <SummaryCard label={t(language, 'statAverage')} value={show(summary.average)} available={available} language={language} />
        <SummaryCard label={t(language, 'statHighest')} value={show(summary.highest)} year={summary.highest_year} available={available} language={language} />
        <SummaryCard label={t(language, 'statLowest')} value={show(summary.lowest)} year={summary.lowest_year} available={available} language={language} />
      </div>

      {/* --- What it means, and the hand-off ------------------------------- */}
      <Panel title={t(language, 'aiClimateInsight')}>
        {available ? (
          <>
            <p className="text-[13px] font-bold leading-tight text-ink">
              {t(language, `param${cap(series.parameter)}`)} · {t(language, `trend${cap(trend.direction)}`)}
            </p>
            <p className="mt-1 text-[12px] leading-[1.5] text-ink-soft">
              {interpretation(language, series)}
            </p>
          </>
        ) : (
          <p className="text-[12px] leading-[1.5] text-muted">
            {t(language, 'climateNeedsData')}
          </p>
        )}

        <button
          type="button"
          onClick={() => onAsk?.(askQuestion(language, location, series, available))}
          className="wx-btn wx-btn-primary mt-3 w-full"
        >
          <Icon name="sparkle" size={14} />
          {t(language, 'askAboutTrend')}
        </button>
      </Panel>
    </>
  )
}

/** Rising, falling or steady — as a shape and a word, never a colour alone. */
function TrendBadge({ direction, change, unit }) {
  const language = useStore((s) => s.language)
  const tone = {
    rising: { color: 'var(--color-warning)', glyph: '▲' },
    falling: { color: 'var(--color-safe)', glyph: '▼' },
    steady: { color: 'var(--color-muted)', glyph: '▬' },
  }[direction] ?? { color: 'var(--color-muted)', glyph: '▬' }

  return (
    <span
      className="flex shrink-0 items-center gap-1 rounded-[var(--radius-pill)] px-2 py-[3px]
                 text-[10px] font-bold"
      style={{ color: tone.color, background: `color-mix(in srgb, ${tone.color} 12%, transparent)` }}
    >
      <span aria-hidden="true">{tone.glyph}</span>
      <span>{t(language, `trend${cap(direction)}`)}</span>
      {typeof change === 'number' && change !== 0 && (
        <span className="tabular-nums opacity-80">
          {change > 0 ? '+' : ''}{change}{unit}
        </span>
      )}
    </span>
  )
}

/**
 * One of the three summary figures.
 *
 * Shows an em dash and "awaiting historical data" rather than a zero when there
 * is nothing to show — a zero here reads as a measurement of zero.
 */
function SummaryCard({ label, value, year, available, language }) {
  return (
    <div className="glass min-w-0 p-2.5">
      <p className="wx-eyebrow truncate">{label}</p>
      <p className="mt-1 truncate text-[16px] font-bold tabular-nums leading-tight text-ink">
        {value}
      </p>
      <p className="mt-px truncate text-[9.5px] text-faint">
        {available ? (year ?? '') : t(language, 'awaitingData')}
      </p>
    </div>
  )
}

function YearField({ label, value, min, max, onChange }) {
  return (
    <label className="min-w-0 flex-1">
      <span className="wx-eyebrow mb-1 block">{label}</span>
      <input
        type="number"
        inputMode="numeric"
        value={value}
        min={min}
        max={max}
        onChange={(event) => {
          const next = Number(event.target.value)
          if (Number.isFinite(next)) onChange(Math.max(min, Math.min(max, next)))
        }}
        className="wx-field tabular-nums"
      />
    </label>
  )
}

const cap = (word) => String(word ?? '').charAt(0).toUpperCase() + String(word ?? '').slice(1)

/** Which of the three absences this is, in the reader's language. */
function noteText(language, note) {
  return t(
    language,
    {
      archive_unavailable: 'climateNoArchive',
      not_enough_years: 'climateTooFewYears',
      no_daily_series: 'climateNoSeries',
    }[note] ?? 'climateNoArchive',
  )
}

/**
 * What the series says, stated from the series.
 *
 * Every value substituted here is one the archive returned. There is no
 * sentence in this function that can be true of one dataset and printed over
 * another.
 */
function interpretation(language, series) {
  const decimals = series.unit === 'mm' ? 0 : 1
  return t(language, `climateReading${cap(series.trend.direction)}`)
    .replace('{param}', t(language, `param${cap(series.parameter)}`).toLowerCase())
    .replace('{from}', String(series.start_year))
    .replace('{to}', String(series.end_year))
    .replace('{change}', `${Math.abs(series.trend.change ?? 0).toFixed(decimals)}${series.unit}`)
    .replace('{average}', `${(series.summary.average ?? 0).toFixed(decimals)}${series.unit}`)
}

/**
 * The question handed to the assistant.
 *
 * Carries the location, the parameter, the window and — when there is one — the
 * measured trend, so the answer is about what is on screen rather than a fresh
 * generic question. When there is no data it says so, which is what stops the
 * assistant being asked to interpret a series that does not exist.
 */
function askQuestion(language, location, series, available) {
  const place = location?.name ?? ''
  if (!available) {
    return t(language, 'askTrendNoData').replace('{place}', place)
  }
  return t(language, 'askTrendTemplate')
    .replace('{param}', t(language, `param${cap(series.parameter)}`).toLowerCase())
    .replace('{place}', place)
    .replace('{from}', String(series.start_year))
    .replace('{to}', String(series.end_year))
}
