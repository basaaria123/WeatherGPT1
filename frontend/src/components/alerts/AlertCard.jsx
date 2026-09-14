import { motion } from 'framer-motion'
import { t } from '../../i18n/ui'
import { useStore } from '../../store/useStore'
import SpokenAdvice from '../audio/SpokenAdvice'
import Icon from '../ui/Icon'
import { isActionable, severityOf } from '../ui/severity'

/**
 * A warning, drawn the way the reference draws one.
 *
 * One component, two homes: the top of Home carries the worst one live for the
 * selected place, and the Alerts destination lists them all. They were two
 * different cards before, which is how a warning came to look more urgent on
 * one screen than the other for the same weather.
 *
 *   [ SEVERE ]                        [ WeatherGPT ]
 *   Severe Thunderstorm Warning
 *   ⌖ Hyderabad, Telangana
 *   ◷ 16:00
 *   Expected impact: …
 *   Recommendation: …
 *   [ View Details ]  [ ◂)) Listen ]
 *
 * ON THE SOURCE CHIP. The reference prints "Official Source" here. This app has
 * no official feed wired into it — every row is WeatherGPT's own reading of
 * measured conditions, produced by the risk engine — so the chip names
 * WeatherGPT instead. Printing "Official Source" over a model's output is the
 * one claim this product must never make, and it is the single place this
 * rebuild deliberately departs from the reference image.
 */

/** The badge is solid at the two bands that mean act now, tinted below them. */
const SOLID = new Set(['Severe', 'High'])

export default function AlertCard({
  alert,
  isNew = false,
  compact = false,
  onViewArea,
  onViewDetails,
}) {
  const language = useStore((s) => s.language)
  const tone = severityOf(alert.severity)
  const urgent = isActionable(alert.severity)
  const solid = SOLID.has(alert.severity)
  const actions = alert.actions_localised?.length ? alert.actions_localised : alert.actions
  const when = formatTime(alert.timestamp)

  return (
    <motion.article
      layout
      data-testid="alert-card"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
      className="wx-note relative min-w-0 overflow-hidden p-3.5"
      style={{
        '--wx-note-line': `color-mix(in srgb, ${tone.color} 34%, transparent)`,
        '--wx-note-fill': `color-mix(in srgb, ${tone.color} 5%, var(--wx-surface))`,
      }}
    >
      {/* A single wash that fades once, when a warning first arrives. It is not
          a loop: a pulsing card is unreadable for exactly as long as it
          matters. */}
      {isNew && (
        <motion.span
          aria-hidden="true"
          className="absolute inset-0"
          style={{ background: tone.color, opacity: 0.16 }}
          initial={{ opacity: 0.28 }}
          animate={{ opacity: 0 }}
          transition={{ duration: 1.6 }}
        />
      )}

      <div className="relative flex min-w-0 items-center gap-2">
        <span
          className={`inline-flex items-center gap-1 rounded-[var(--radius-pill)] px-2 py-[3px]
                      text-[9.5px] font-bold uppercase tracking-[0.07em] ${urgent ? 'pulse-alert' : ''}`}
          style={
            solid
              ? { background: tone.color, color: '#fff' }
              : { background: tone.tint, color: tone.ink }
          }
        >
          <Icon name="warning" size={10} stroke={2.2} />
          {alert.severity_label ?? alert.severity}
        </span>

        {/* Provenance, stated plainly — see the note at the top of this file. */}
        <span
          className="ml-auto shrink-0 rounded-[var(--radius-pill)] bg-[rgb(var(--wx-tint)/0.07)]
                     px-2 py-[3px] text-[9.5px] font-semibold text-muted"
        >
          WeatherGPT
        </span>
      </div>

      <h3
        className="relative mt-2 text-[14px] font-bold leading-tight tracking-[-0.01em]"
        style={{ color: solid ? tone.color : 'var(--color-ink)' }}
      >
        {alert.hazard_label ?? alert.alert_type}
      </h3>

      <div className="relative mt-1.5 space-y-1">
        {alert.location && (
          <p className="flex min-w-0 items-center gap-1.5 text-[11.5px] text-muted">
            <Icon name="pin" size={12} className="text-faint" />
            <span className="min-w-0 truncate">{alert.location}</span>
          </p>
        )}
        {when && (
          <p className="flex items-center gap-1.5 text-[11.5px] text-muted">
            <Icon name="clock" size={12} className="text-faint" />
            <time dateTime={alert.timestamp}>{when}</time>
          </p>
        )}
      </div>

      {alert.message && (
        <p className="relative mt-2 text-[12px] leading-[1.45] text-ink-soft">
          <span className="font-semibold">{t(language, 'expectedImpact')}: </span>
          {alert.message}
        </p>
      )}

      {/* One recommendation on the card. The rest are a tap away rather than a
          scroll: a card with six numbered steps stops being a warning. */}
      {actions?.length > 0 && (
        <p className="relative mt-1 text-[12px] leading-[1.45] text-ink-soft">
          <span className="font-semibold">{t(language, 'recommended')}: </span>
          {actions[0]}
          {actions.length > 1 && !compact && (
            <span className="text-muted"> (+{actions.length - 1})</span>
          )}
        </p>
      )}

      {alert.historical_comparison && !compact && (
        <p className="relative mt-2 rounded-[var(--radius-control)] bg-[rgb(var(--wx-tint)/0.05)] px-2.5 py-1.5
                      text-[11px] leading-[1.45] text-muted">
          {alert.historical_comparison.sentence}
        </p>
      )}

      <div className="relative mt-3 flex min-w-0 flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => (onViewDetails ? onViewDetails(alert) : onViewArea?.(alert))}
          className="wx-btn wx-btn-primary min-w-0 flex-1"
        >
          {t(language, 'viewDetails')}
        </button>

        {/* The alert's own actions, said aloud. `advice` is the script that
            answers "what do I do", which is what a warning is asking. */}
        <AlertListen alert={alert} />
      </div>

      {/* Kept as a separate, quieter control: "where is this?" is a different
          question from "what do I do about it?", and the reference gives the
          card exactly two buttons. */}
      {onViewArea && alert.latitude !== null && alert.latitude !== undefined && !compact && (
        <button
          type="button"
          onClick={() => onViewArea(alert)}
          className="relative mt-2 text-[11px] font-semibold text-primary transition hover:opacity-75"
        >
          {t(language, 'viewArea')} →
        </button>
      )}
    </motion.article>
  )
}

/**
 * The Listen button in its reference shell.
 *
 * `SpokenAdvice` owns everything hard about playback — provider order, the
 * pause/replay states, the one-voice-at-a-time lock — so this is only the
 * wrapper that gives it the deep navy the reference paints it and keeps it the
 * same height as the button beside it.
 */
function AlertListen({ alert }) {
  const userType = useStore((s) => s.userType)
  return (
    <span className="min-w-0 flex-1 [&_button]:w-full [&_button]:justify-center [&_button]:rounded-[var(--radius-control)]
                     [&_button]:px-3 [&_button]:py-[9px] [&>div]:mt-0">
      <SpokenAdvice location={alert.location} userType={userType} topic="advice" compact />
    </span>
  )
}

function formatTime(iso) {
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
}
