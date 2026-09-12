import { motion } from 'framer-motion'
import { hazardLabel, levelLabel, t } from '../../i18n/ui'
import { useStore } from '../../store/useStore'
import { severityOf } from '../ui/severity'

/**
 * The map's location preview — step one of two.
 *
 * Selecting a marker opens this and nothing else: the reader stays on the map,
 * the dashboard behind it keeps showing whatever it was showing, and only the
 * call to action at the bottom commits the place. That separation is the whole
 * point of the box, so it says so in as many words at the foot of it.
 *
 * It is a preview, not a second dashboard: eight short things in the order a
 * reader needs them — where, how bad, in what words, from what hazard, what
 * else is going on, when it bites, what it means, and the one way onward.
 */

const BANDS = ['Low', 'Moderate', 'High', 'Severe']

/** "16:00" from an ISO stamp. Digits read the same in every language. */
function clock(stamp) {
  const text = String(stamp ?? '')
  return text.includes('T') ? text.split('T')[1].slice(0, 5) : text
}

/**
 * The run of hours around the peak that stay at the peak's level.
 *
 * Returns nothing when the peak is Low: an "expected window" for a day with no
 * hazard in it is a sentence about nothing, and the box is better one line
 * shorter than padded with one.
 */
function riskWindow(hours) {
  if (!hours?.length) return null
  let peak = 0
  for (let i = 1; i < hours.length; i += 1) {
    if ((hours[i].risk_score ?? 0) > (hours[peak].risk_score ?? 0)) peak = i
  }
  const level = hours[peak].risk_level ?? 'Low'
  if (level === 'Low') return null

  let from = peak
  let to = peak
  while (from > 0 && hours[from - 1].risk_level === level) from -= 1
  while (to < hours.length - 1 && hours[to + 1].risk_level === level) to += 1
  return { level, from: clock(hours[from].time), to: clock(hours[to].time), single: from === to }
}

/** Temperature, rain chance and wind — only the ones actually measured. */
function secondaryConditions(entry, language) {
  const rows = []
  const has = (value) => Number.isFinite(value)
  if (has(entry.temperature_c)) {
    rows.push([t(language, 'layerTemperature'), `${Math.round(entry.temperature_c)}°`])
  }
  if (has(entry.precipitation_probability_pct)) {
    rows.push([t(language, 'rainChance'), `${Math.round(entry.precipitation_probability_pct)}%`])
  }
  if (has(entry.wind_speed_kmh)) {
    rows.push([t(language, 'wind'), `${Math.round(entry.wind_speed_kmh)} km/h`])
  }
  return rows
}

export default function RiskDetail({ entry, isActive, activeName, onCommit, onAsk, onClose }) {
  const language = useStore((s) => s.language)
  const tone = severityOf(entry.risk_level)
  const band = Math.max(0, BANDS.indexOf(entry.risk_level)) + 1
  const peak = riskWindow(entry.hours)
  const conditions = secondaryConditions(entry, language)

  return (
    <motion.aside
      data-testid="risk-detail"
      initial={{ opacity: 0, y: 10, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.985 }}
      transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
      /* A bottom sheet on a narrow screen, a card in the top corner on a wide
         one. Both sit inside the map's own box rather than over the viewport,
         so the map stays visible above the sheet and the marker stays findable. */
      className="pointer-events-auto absolute inset-x-2 bottom-2 z-[900] flex max-h-[66%] flex-col
                 overflow-hidden rounded-[var(--radius-card)] border border-[rgb(var(--wx-tint)/0.14)]
                 bg-[rgb(var(--wx-scrim)/0.96)] shadow-2xl backdrop-blur-md
                 sm:inset-x-auto sm:bottom-auto sm:left-3 sm:top-3 sm:max-h-[calc(100%-1.5rem)] sm:w-[19.5rem]"
    >
      {/* The reading scrolls; the control that acts on it never does. A longer
          translation or a busier location must not push the call to action out
          of a sheet the reader cannot tell is scrollable. */}
      <div className="min-h-0 flex-1 overflow-y-auto p-3 pb-2">
        {/* 1 — where */}
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-semibold leading-tight text-ink">{entry.location}</p>
            {entry.admin1 && entry.admin1 !== entry.location && (
              <p className="truncate text-[11px] text-muted">{entry.admin1}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t(language, 'closeCompare')}
            className="-mr-1 -mt-1 shrink-0 rounded-lg px-2 py-1 text-[13px] leading-none text-muted
                       transition hover:bg-[rgb(var(--wx-tint)/0.10)] hover:text-ink"
          >
            ×
          </button>
        </div>

        {/* 2 and 3 — the score, then the word for it. Never colour alone: the
            shape, the glyph, the label and the count of filled segments all
            carry the band, so it survives greyscale and colour blindness. */}
        <div className="mt-2.5 flex items-baseline gap-2">
          <span className="text-[26px] font-semibold leading-none text-ink tabular-nums">
            {entry.risk_score}
          </span>
          <span className="text-[12px] text-faint">/100</span>
          <span
            className="ml-auto flex items-center gap-1 rounded-[var(--radius-pill)] px-2 py-0.5 text-[11px] font-semibold"
            style={{ color: tone.ink, background: tone.tint }}
          >
            <span aria-hidden="true">{tone.icon}</span>
            {levelLabel(language, entry.risk_level)}
            <span aria-hidden="true" className="opacity-70">{tone.glyph}</span>
          </span>
        </div>

        <div className="mt-2 flex gap-1" role="img"
             aria-label={`${entry.risk_score}/100 — ${levelLabel(language, entry.risk_level)}`}>
          {BANDS.map((level, index) => (
            <span
              key={level}
              className="h-1.5 flex-1 rounded-full"
              style={{
                background: index < band ? tone.color : 'rgb(var(--wx-tint) / 0.14)',
              }}
            />
          ))}
        </div>

        {/* 4 — the hazard itself */}
        <p className="mt-2.5 text-[12px] font-medium text-ink-soft">
          {entry.detected_hazard && entry.detected_hazard !== 'None'
            ? hazardLabel(language, entry.detected_hazard)
            : t(language, 'noHazard')}
        </p>

        {/* 5 — what else is going on, at a glance */}
        {conditions.length > 0 && (
          <dl className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
            {conditions.map(([label, value]) => (
              <div key={label} className="flex items-baseline gap-1">
                <dt className="text-[10.5px] uppercase tracking-wide text-faint">{label}</dt>
                <dd className="text-[12px] font-medium text-ink-soft tabular-nums">{value}</dd>
              </div>
            ))}
          </dl>
        )}

        {/* 6 — when it is expected to bite */}
        {peak && (
          <p className="mt-2 text-[11.5px] text-muted">
            {peak.single
              ? t(language, 'peakRisk')
                  .replace('{level}', levelLabel(language, peak.level))
                  .replace('{time}', peak.from)
              : t(language, 'riskWindow').replace('{from}', peak.from).replace('{to}', peak.to)}
          </p>
        )}

        {/* 7 — the one sentence. Written by the backend in the reader's language
            and for their role, from this location's own forecast hours. */}
        {entry.insight && (
          <p className="mt-2.5 line-clamp-2 border-l-2 border-primary/40 pl-2 text-[11.5px] leading-relaxed text-ink-soft">
            <span className="font-semibold text-primary">{t(language, 'weatherGptSays')}: </span>
            {entry.insight}
          </p>
        )}

      </div>

      {/* 8 — the two controls that act on the selection. Both move the reader;
          one takes them to the dashboard for this place, the other takes them
          to a conversation about it. */}
      <div className="shrink-0 border-t border-[rgb(var(--wx-tint)/0.08)] px-3 pb-3 pt-2.5">
        {onAsk && (
          <button
            type="button"
            data-testid="ask-about-area"
            onClick={onAsk}
            className="mb-2 w-full rounded-lg border border-[rgb(var(--wx-tint)/0.28)] px-3 py-2
                       text-[12.5px] font-semibold text-ink transition
                       hover:bg-[rgb(var(--wx-tint)/0.12)]"
          >
            {t(language, 'askAboutArea')}
          </button>
        )}
        {isActive ? (
          <p className="rounded-lg bg-primary/[0.08] px-2 py-1.5 text-center text-[11.5px] font-semibold text-primary">
            {t(language, 'shownAbove')}
          </p>
        ) : (
          <>
            <button
              type="button"
              data-testid="view-local-details"
              onClick={onCommit}
              className="w-full rounded-lg border border-primary/45 bg-primary/[0.12] px-3 py-2
                         text-[12.5px] font-semibold text-ink transition
                         hover:border-primary/70 hover:bg-primary/20"
            >
              {t(language, 'openLocalDetail')} →
            </button>
            {/* Says out loud what closing the box will and will not do. */}
            {activeName && (
              <p className="mt-1.5 text-center text-[10.5px] leading-snug text-faint">
                {t(language, 'previewOnly').replace('{name}', activeName)}
              </p>
            )}
          </>
        )}
      </div>
    </motion.aside>
  )
}
