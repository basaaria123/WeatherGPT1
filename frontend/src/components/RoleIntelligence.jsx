import { AnimatePresence, motion } from 'framer-motion'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { isLatinText } from '../i18n/scriptSupport'
import { levelLabel, t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { LoadingBlock, Panel } from './ui/Primitives'

/**
 * What the weather means for whoever is reading it.
 *
 * Rendered entirely from the backend's `role_intelligence` block, the same way
 * the impact grid renders `impacts`: this component interprets nothing, scores
 * nothing, and knows nothing about farming or the sea. A card the server did
 * not send simply does not appear, which is what stops the interface inventing
 * a reading the data could not support.
 *
 * The panel changes when the profile changes because `/weather/current` already
 * takes `user_type` and is already refetched on that change — no new request,
 * and no second weather system.
 */

// Readings that close on a "when" — a departure hour, a working window, a sea
// state that turns. For everyone else the hour strip would be data with no
// decision attached to it.
const TIMING_ROLES = ['fisherman', 'commuter', 'driver', 'outdoor_worker', 'student']

// Presentation only. `tone` is the server's word for how a card should look,
// never a claim in itself, and it maps onto the palette the rest of the app
// already uses for severity.
const TONES = {
  safe: { color: 'var(--color-safe)', tint: 'rgb(52 211 153 / 0.12)', ring: 'rgb(52 211 153 / 0.38)', icon: '●' },
  caution: { color: 'var(--color-caution)', tint: 'rgb(251 191 36 / 0.12)', ring: 'rgb(251 191 36 / 0.38)', icon: '▲' },
  warn: { color: 'var(--color-warning)', tint: 'rgb(251 146 60 / 0.14)', ring: 'rgb(251 146 60 / 0.44)', icon: '▲' },
  danger: { color: 'var(--color-danger)', tint: 'rgb(244 63 94 / 0.15)', ring: 'rgb(244 63 94 / 0.5)', icon: '◆' },
  info: { color: 'var(--color-muted)', tint: 'rgb(var(--wx-tint) / 0.06)', ring: 'rgb(var(--wx-tint) / 0.14)', icon: '·' },
}

const toneOf = (tone) => TONES[tone] ?? TONES.info

export default function RoleIntelligence({ intel, loading, hours }) {
  const language = useStore((s) => s.language)
  const reduced = useReducedMotion()

  if (loading && !intel) {
    return (
      <Panel title={t(language, 'roleIntelligence')}>
        <LoadingBlock label={t(language, 'insightLoading')} lines={3} />
      </Panel>
    )
  }

  if (!intel?.cards?.length) {
    // A backend that has not been updated, or a reading it could not make.
    // Either way the rest of the dashboard is unaffected.
    return null
  }

  const heading = intel.heading || t(language, 'roleIntelligence')
  // Only the roles whose question is about timing get the strip, and only when
  // the hourly series the rest of the app already fetched actually has hours.
  const showTimeline = TIMING_ROLES.includes(intel.user_type) && (hours?.length ?? 0) >= 6

  return (
    <Panel
      title={t(language, 'roleIntelligence')}
      action={
        /* `min-w-0` is what lets `truncate` work here: without it the flex
           item refuses to shrink below its text and pushes a 320px page
           sideways. */
        <span className="flex min-w-0 items-center gap-1.5 text-[11px] text-muted">
          <span aria-hidden="true" className="shrink-0">{intel.icon}</span>
          <span className="truncate">{heading}</span>
        </span>
      }
    >
      {/* Only this panel transitions when the profile changes; the dashboard
          around it does not move. */}
      <AnimatePresence mode="wait">
        <motion.div
          key={`${intel.user_type}:${language}`}
          initial={reduced ? { opacity: 0 } : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduced ? { opacity: 0 } : { opacity: 0, y: -8 }}
          transition={{ duration: reduced ? 0.12 : 0.26, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="grid min-w-0 gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
            {intel.cards.map((card) => (
              <RoleCard key={card.id} card={card} />
            ))}
          </div>

          {showTimeline && <HourStrip hours={hours} language={language} userType={intel.user_type} />}

          {/* The disclosure, where the app cannot answer a role's real
              question. It is part of the reading, not a footnote to skip. */}
          {intel.note && (
            <p className="mt-3 border-t border-[rgb(var(--wx-tint)/0.07)] pt-2.5 text-[11px] leading-relaxed text-faint">
              {intel.note}
            </p>
          )}
        </motion.div>
      </AnimatePresence>
    </Panel>
  )
}

function RoleCard({ card }) {
  const tone = toneOf(card.tone)
  return (
    <div
      className="min-w-0 rounded-[var(--radius-card)] border bg-[rgb(var(--wx-tint)/0.03)] p-3"
      style={{ borderColor: tone.ring }}
    >
      {/* Uppercase and letter-spacing are Latin devices; on Devanagari or
          Telugu the tracking pulls conjuncts apart, so the title takes them
          only when it is Latin. */}
      <div
        className={`flex items-center gap-1.5 text-faint ${
          isLatinText(card.title) ? 'text-[10px] uppercase tracking-[0.12em]' : 'text-[11px]'
        }`}
      >
        <span aria-hidden="true" className="text-[12px]">{card.icon}</span>
        <span className="truncate">{card.title}</span>
      </div>

      <div className="mt-1.5 flex items-start gap-1.5">
        {/* Never colour alone: the glyph carries the same meaning in greyscale
            and for a colour-blind reader, as everywhere else in this app. */}
        <span aria-hidden="true" className="mt-[3px] text-[10px]" style={{ color: tone.color }}>
          {tone.icon}
        </span>
        <p className="min-w-0 text-[13px] font-semibold leading-snug" style={{ color: tone.color }}>
          {card.headline}
        </p>
      </div>

      {card.detail && <p className="mt-1.5 text-[11.5px] leading-relaxed text-muted">{card.detail}</p>}
    </div>
  )
}

/**
 * The next twelve hours, coloured by the risk the engine already scored.
 *
 * This invents no schedule of its own — each block is one hour from the
 * timeline the dashboard is already showing, carrying that hour's own
 * `risk_level`. It answers "when", which is the question both of these roles
 * are actually asking.
 */
function HourStrip({ hours, language, userType }) {
  const window = hours.slice(0, 12)
  const label = userType === 'fisherman' ? t(language, 'fishingWindow') : t(language, 'commuteWindow')

  return (
    <div className="mt-3 min-w-0 border-t border-[rgb(var(--wx-tint)/0.07)] pt-3">
      <div
        className={`mb-2 text-faint ${
          isLatinText(label) ? 'text-[10px] uppercase tracking-[0.12em]' : 'text-[11px]'
        }`}
      >
        {label}
      </div>
      <div className="scroll-x flex min-w-0 gap-1.5 pb-1">
        {window.map((hour) => {
          const tone = toneOf(
            hour.risk_level === 'Severe' ? 'danger'
              : hour.risk_level === 'High' ? 'warn'
                : hour.risk_level === 'Moderate' ? 'caution' : 'safe',
          )
          const time = String(hour.time ?? '').split('T')[1]?.slice(0, 5) ?? ''
          return (
            <div
              key={hour.time}
              title={`${time} · ${levelLabel(language, hour.risk_level)}`}
              className="flex shrink-0 flex-col items-center gap-1 rounded-lg border px-2 py-1.5"
              style={{ borderColor: tone.ring, background: tone.tint }}
            >
              <span aria-hidden="true" className="text-[9px]" style={{ color: tone.color }}>{tone.icon}</span>
              <span className="text-[10px] tabular-nums text-muted">{time}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
