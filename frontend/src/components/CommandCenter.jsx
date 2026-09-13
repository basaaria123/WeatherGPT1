import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { relativeLabel } from '../i18n/datetime'
import { hazardLabel, t } from '../i18n/ui'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { useStore } from '../store/useStore'
import { severityOf } from './ui/severity'
import { LoadingBlock, Metric, SeverityPill } from './ui/Primitives'
import SpokenAdvice from './audio/SpokenAdvice'
import WeatherGlyph from './ui/WeatherGlyph'
import WeatherCompass from './WeatherCompass'
import WeatherMicroBurst from './WeatherMicroBurst'
import Icon from './ui/Icon'

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

// `night` is resolved once, in App, from the same response this card renders —
// passed down rather than recomputed here so the icon, the theme and the sky
// behind them cannot answer the question differently.
export default function CommandCenter({ data, loading, error, onRetry, night = false }) {
  const language = useStore((s) => s.language)
  // Only used to word the compass heading — the role itself is untouched.
  const userType = useStore((s) => s.userType)
  // Bumped on each tap of the weather icon; the burst restarts on a new value.
  const [burst, setBurst] = useState(0)
  const reduced = useReducedMotion()

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
  const updated = relativeLabel(data.generated_at, language)
  const officialCount = data.official_alert_count ?? 0

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      /* The hover response is deliberately almost nothing: a degree of lift and
         a slightly brighter edge, on a card that is otherwise perfectly still.
         The lift is framer's rather than a Tailwind class because framer writes
         its own inline `transform` here, which a class could not override. */
      whileHover={reduced ? undefined : { y: -2 }}
      className="glass glass-hero relative min-w-0 overflow-hidden p-4"
    >
      {/* Sits behind the card's own content, filling it, and unmounts when the
          burst ends. */}
      <WeatherMicroBurst token={burst} weatherCode={current.weather_code} />

      {/* --- Heading row: what this is, and how fresh it is --------------- */}
      <div className="mb-2.5 flex min-w-0 items-center gap-2">
        <h2 className="wx-eyebrow min-w-0">{t(language, 'conditionsNow')}</h2>
        {/* Which sky the reading below was taken under. It does not restate
            the weather — the condition line does that in the provider's own
            words. */}
        {night && (
          <span
            data-testid="night-badge"
            className="inline-flex items-center gap-1 rounded-[var(--radius-pill)]
                       bg-[rgb(var(--wx-tint)/0.08)] px-1.5 py-px text-[9.5px] font-semibold
                       uppercase tracking-[0.07em] text-ink-soft"
          >
            <Icon name="moon" size={10} />
            {t(language, 'nightLabel')}
          </span>
        )}
        {updated && (
          <span className="ml-auto shrink-0 text-[10px] text-faint">
            {t(language, 'updated')} {updated}
          </span>
        )}
      </div>

      {/* --- The reading, and the score beside it ------------------------- */}
      <div className="flex min-w-0 items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-2.5">
            {/* Tapping the icon replays the current condition. It is a button
                so it is reachable by keyboard too. */}
            <button
              type="button"
              onClick={() => setBurst((n) => n + 1)}
              aria-label={current.condition ?? t(language, 'conditionsNow')}
              title={current.condition ?? undefined}
              className="shrink-0 rounded-2xl transition active:scale-95"
            >
              {/* Keyed on the code so a new location's weather fades in rather
                  than swapping between two unrelated pictures. */}
              <AnimatePresence mode="wait" initial={false}>
                <motion.span
                  key={`${current.weather_code ?? 'none'}-${night ? 'n' : 'd'}`}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
                  className="block"
                >
                  <WeatherGlyph code={current.weather_code} isDay={!night} size={46} />
                </motion.span>
              </AnimatePresence>
            </button>

            {current.temperature_c !== null && current.temperature_c !== undefined && (
              <div className="flex items-start leading-none">
                <span className="text-[42px] font-bold tracking-[-0.03em] text-ink">
                  <AnimatedNumber value={current.temperature_c} decimals={0} />
                </span>
                <span className="mt-[6px] text-[15px] font-semibold text-muted">°C</span>
              </div>
            )}
          </div>

          {current.condition && (
            <p className="mt-1.5 truncate text-[14px] font-semibold capitalize text-ink-soft">
              {current.condition}
            </p>
          )}
          {current.apparent_temperature_c !== null && current.apparent_temperature_c !== undefined && (
            <p className="mt-px text-[11.5px] text-muted">
              {t(language, 'feelsLike')} {current.apparent_temperature_c.toFixed(0)}°C
            </p>
          )}
          <p className="mt-px truncate text-[11px] text-faint">
            {location?.name}
            {location?.admin1 && location.admin1 !== location.name ? `, ${location.admin1}` : ''}
          </p>

          {/* What is happening, in a sentence. Says none of the numbers beside
              it — a listener cannot hold "humidity 82%" and would not act on
              it. */}
          <SpokenAdvice location={location?.name} userType={userType} topic="conditions" compact />
        </div>

        {risk && <RiskExplainer risk={risk} language={language} />}
      </div>

      {/* --- The nine readings -------------------------------------------
          Three columns, in the reference's order. Every one is guarded by
          `Metric`, so a value the provider did not send is absent rather than
          shown as a dash. */}
      <div className="mt-3.5 grid grid-cols-3 gap-x-3 gap-y-3 border-t border-[var(--wx-border)] pt-3">
        <Metric label={t(language, 'feelsLike')} value={current.apparent_temperature_c?.toFixed?.(0)} unit="°C" />
        <Metric label={t(language, 'humidity')} value={current.humidity_pct?.toFixed?.(0)} unit="%" />
        <Metric label={t(language, 'wind')} value={current.wind_speed_kmh?.toFixed?.(0)} unit="km/h" />
        <Metric label={t(language, 'gusts')} value={current.wind_gust_kmh?.toFixed?.(0)} unit="km/h" />
        <Metric label={t(language, 'rainChance')} value={current.precipitation_probability_pct?.toFixed?.(0)} unit="%" />
        <Metric label={t(language, 'precipitation')} value={current.precipitation_mm?.toFixed?.(1)} unit="mm" />
        <Metric label={t(language, 'pressure')} value={current.pressure_hpa?.toFixed?.(0)} unit="hPa" />
        <Metric label={t(language, 'cloud')} value={current.cloud_cover_pct?.toFixed?.(0)} unit="%" />
        <Metric label={t(language, 'visibility')} value={current.visibility_km?.toFixed?.(1)} unit="km" />
      </div>

      {/* A detected hazard and an issued warning are different claims, so they
          are shown as two separate statements rather than one badge. */}
      {risk && <HazardVsAlerts risk={risk} officialCount={officialCount} language={language} />}

      {/* Wind has a direction as well as a speed, and the grid above can only
          show the speed. The dial reads the same payload — no second request,
          no second interpretation. */}
      <div className="mt-3.5 border-t border-[var(--wx-border)] pt-3.5">
        <WeatherCompass current={current} language={language} userType={userType} />
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
  const bands = useStore((s) => s.capabilities?.risk_bands)
  const tone = severityOf(risk.risk_level)

  const contributors = Object.entries(risk.hazard_scores ?? {})
    .filter(([, score]) => score >= 1)
    .sort((a, b) => b[1] - a[1])

  return (
    <div className="w-[41%] shrink-0">
      {/* Attributed, not just labelled. A number this prominent has to say
          whose number it is, or a reader will take it for an official one. */}
      <div className="wx-eyebrow leading-[1.35]">{t(language, 'aiHazard')}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="text-[28px] font-bold leading-none tracking-[-0.02em]" style={{ color: tone.color }}>
          {risk.risk_score}
        </span>
        <span className="text-[12px] font-semibold text-muted">/100</span>
      </div>
      <p className="mt-1 text-[10.5px] leading-[1.45] text-faint">{t(language, 'riskBasis')}</p>

      {(contributors.length > 0 || risk.drivers?.length > 0) && (
        <>
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            className="mt-1.5 inline-flex items-center gap-1 text-[10.5px] font-semibold text-primary
                       underline underline-offset-2 transition hover:opacity-80"
          >
            {t(language, 'whyThisScore')}
            <Icon name="chevronDown" size={10} className={open ? 'rotate-180' : ''} />
          </button>

          {open && (
            <div className="mt-2 rounded-[var(--radius-control)] bg-[rgb(var(--wx-tint)/0.05)] p-2.5 text-left">
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
                            style={{ width: `${score}%`, background: severityOf(levelFor(score, bands)).color }}
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

/**
 * Band for a sub-score, read from the engine's own bands.
 *
 * /config publishes `risk_bands`, so this reads them rather than restating the
 * boundaries. Re-declaring them here would be a second source of truth for
 * severity, which is exactly what the risk engine exists to prevent — the
 * literals below are only a last resort if /config has not loaded yet.
 */
function levelFor(score, bands) {
  const table = bands?.length ? bands : FALLBACK_BANDS
  const band = table.find((b) => score >= b.min && score <= b.max)
  return band?.level ?? 'Low'
}

const FALLBACK_BANDS = [
  { level: 'Low', min: 0, max: 30 },
  { level: 'Moderate', min: 31, max: 60 },
  { level: 'High', min: 61, max: 80 },
  { level: 'Severe', min: 81, max: 100 },
]

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
    <div className="mt-3.5 grid gap-3 border-t border-[var(--wx-border)] pt-3 min-[360px]:grid-cols-2">
      <div className="min-w-0">
        <div className="wx-eyebrow flex items-start gap-1.5">
          <Icon name="shield" size={12} className="mt-px" style={{ color: tone.color }} />
          <span className="min-w-0">{t(language, 'hazardRisk')}</span>
        </div>
        <div className="mt-1 flex items-center gap-1.5">
          {hasHazard && <span aria-hidden="true" className="text-[11px]" style={{ color: tone.color }}>{tone.icon}</span>}
          <span className="min-w-0 text-[13px] font-bold leading-tight text-ink">
            {hasHazard ? hazardLabel(language, risk.detected_hazard) : t(language, 'noHazard')}
          </span>
        </div>
        {/* Only worth saying while no warning exists. Once one is issued the
            note would contradict the panel beside it. */}
        {/* The disclaimer stands whether or not a hazard was detected: the
            distinction between a model's reading and a government's warning is
            not conditional on the weather. */}
        <p className="mt-1 text-[10.5px] leading-[1.45] text-faint">
          {hasHazard && officialCount === 0
            ? t(language, 'hazardDetectedNote')
            : t(language, 'aiHazardNote')}
        </p>
      </div>

      {/* What this counts is warnings *this app* has raised and stored for this
          place. It was headed "Official alert status" and credited "IMD / NDMA"
          — a source that is not wired into this build and never was. The count
          comes from the same store the alerts destination reads, which the risk
          engine fills; crediting an agency for it would be the one claim this
          product must never make. */}
      <div className="min-w-0">
        <div className="wx-eyebrow flex items-start gap-1.5">
          <Icon name="bell" size={12} className={`mt-px ${officialCount > 0 ? 'text-danger' : 'text-muted'}`} />
          <span className="min-w-0">{t(language, 'warningsRaised')}</span>
        </div>
        <div className="mt-1 flex items-start gap-1.5">
          <Icon
            name={officialCount > 0 ? 'warning' : 'check'}
            size={12}
            className={`mt-[3px] ${officialCount > 0 ? 'text-danger' : 'text-safe'}`}
          />
          <span className="min-w-0 text-[13px] font-bold leading-tight text-ink">
            {officialCount === 0
              ? t(language, 'alertHistoryEmpty')
              : officialCount === 1
                ? t(language, 'warningOne')
                : t(language, 'warningMany').replace('{n}', String(officialCount))}
          </span>
        </div>
        <p className="mt-1 text-[10.5px] text-faint">{t(language, 'source')}: WeatherGPT</p>
      </div>
    </div>
  )
}
