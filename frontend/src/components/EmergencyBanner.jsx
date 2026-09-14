import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { hazardLabel, levelLabel, t } from '../i18n/ui'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { useStore } from '../store/useStore'
import { severityOf } from './ui/severity'
import Icon from './ui/Icon'
import { browserSpeechSupported, utteranceFor } from '../audio/speech'

/**
 * Emergency banner.
 *
 * Rendered only when the backend sets `emergency.active`. There is deliberately
 * no threshold check here — if this component could decide for itself, the
 * interface and the risk engine could disagree, and during a demo they would.
 *
 * Accessibility is treated as correctness, not polish:
 *  - an ARIA live region, so activation is announced rather than only seen;
 *  - severity carried by icon *and* text, never colour alone;
 *  - a slow opacity pulse at most, and none at all under reduced motion —
 *    a fast red flash in an emergency UI is a seizure risk.
 */

// Locale and voice selection both live in audio/speech.js. This file used to
// carry its own six-language table, which is how the emergency button came to
// behave differently from every other Listen control in the app.

function formatUntil(value, language) {
  if (!value) return null
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return null
  return parsed.toLocaleString(language === 'en' ? 'en-IN' : undefined, {
    weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
  })
}

export default function EmergencyBanner({ emergency, audioBase64, audioMime }) {
  const language = useStore((s) => s.language)
  const audibleAlerts = useStore((s) => s.audibleAlerts)
  const reduced = useReducedMotion()
  /**
   * Open, or a single line?
   *
   * Severe opens. High does not — it announces itself in one line and opens on
   * a tap. The full brief is four paragraphs and a numbered list, and at High
   * it pushed the conditions card, the warning card and the advice card off
   * the first screen entirely: a reader on a stormy day scrolled past the
   * emergency to find out what the weather was.
   *
   * Nothing is hidden by this. The line names the hazard and its band, the
   * warning card below carries the same warning in full, and the brief is one
   * tap away — which is a different thing from a banner that has been
   * dismissed, and is why this is not the dismissal state.
   */
  const [dismissed, setDismissed] = useState(emergency?.risk_level !== 'Severe')
  const [speaking, setSpeaking] = useState(false)
  const [voiceNote, setVoiceNote] = useState(null)
  const audioRef = useRef(null)

  const active = Boolean(emergency?.active)
  const hazard = emergency?.hazard

  // A new hazard, or a fresh activation, brings the banner back.
  useEffect(() => {
    if (active) setDismissed(emergency?.risk_level !== 'Severe')
  }, [active, hazard, emergency?.risk_level])

  const stop = () => {
    audioRef.current?.pause()
    audioRef.current = null
    if (browserSpeechSupported()) window.speechSynthesis.cancel()
    setSpeaking(false)
  }

  useEffect(() => () => stop(), [])

  if (!active) return null

  const tone = severityOf(emergency.risk_level)
  const until = formatUntil(emergency.valid_until, language)

  /** Speak the instructions the backend wrote for speech, in the user's language. */
  const speak = () => {
    if (speaking) {
      stop()
      return
    }
    // The complete message, exactly as the card states it. The server writes
    // `spoken_instructions` as headline + what is happening + why it matters +
    // the immediate actions; the headline alone is the fallback, and the rest
    // of the card is assembled here so nothing visible goes unspoken.
    const text =
      emergency.spoken_instructions ||
      [
        emergency.headline,
        emergency.what_is_happening,
        emergency.why_it_matters,
        ...(emergency.immediate_actions ?? []),
      ]
        .filter(Boolean)
        .join(' ')
    if (!text) return
    setVoiceNote(null)

    if (audioBase64) {
      const audio = new Audio(`data:${audioMime ?? 'audio/mpeg'};base64,${audioBase64}`)
      audioRef.current = audio
      audio.onended = () => setSpeaking(false)
      audio.onerror = () => setSpeaking(false)
      audio.play().then(() => setSpeaking(true)).catch(() => setSpeaking(false))
      return
    }
    if (!browserSpeechSupported()) return

    // Through the shared helper, which picks a voice that can actually
    // pronounce this language. Building an utterance here was how this button
    // came to read an emergency as its numbers alone: `lang = 'hi-IN'` is a
    // preference, not a voice, and an English voice handed Devanagari says the
    // digits and nothing else.
    utteranceFor(text, language)
      .then((utterance) => {
        if (!utterance) {
          // No voice for this language on this device. The full message is on
          // the card in front of the reader; say that rather than mis-reading it.
          setSpeaking(false)
          setVoiceNote(t(language, 'voiceNoLanguage'))
          return
        }
        utterance.onend = () => setSpeaking(false)
        utterance.onerror = () => setSpeaking(false)
        window.speechSynthesis.speak(utterance)
        setSpeaking(true)
      })
      .catch(() => setSpeaking(false))
  }

  // Settings decide whether a severe alert is allowed to have a voice at all.
  // It still never speaks on its own — this gates the control, not an autoplay
  // that does not exist.
  const canSpeak = audibleAlerts && (Boolean(audioBase64) || browserSpeechSupported())

  // Dismissed does not mean resolved: a compact indicator stays while the risk
  // does, so a cleared banner can never read as an all-clear.
  if (dismissed) {
    return (
      <button
        type="button"
        onClick={() => setDismissed(false)}
        aria-expanded={false}
        className="wx-note flex w-full min-w-0 items-center gap-2.5 p-3 text-left transition hover:brightness-[0.99]"
        style={{
          '--wx-note-line': `color-mix(in srgb, ${tone.color} 34%, transparent)`,
          '--wx-note-fill': `color-mix(in srgb, ${tone.color} 6%, var(--wx-surface))`,
        }}
      >
        <span
          className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-white ${reduced ? '' : 'pulse-emergency'}`}
          style={{ background: tone.color }}
        >
          <Icon name="warning" size={15} stroke={2.1} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[12.5px] font-bold leading-tight text-ink">
            {t(language, 'stillActive')}
          </span>
          <span className="block truncate text-[11px] text-muted">
            {hazardLabel(language, emergency.hazard)} · {levelLabel(language, emergency.risk_level)}
          </span>
        </span>
        <span className="shrink-0 text-[11px] font-semibold text-primary">
          {t(language, 'emergencyNow')} →
        </span>
      </button>
    )
  }

  return (
    <AnimatePresence>
      <motion.section
        // Announced by screen readers the moment conditions become actionable.
        role="alert"
        aria-live="assertive"
        initial={reduced ? { opacity: 0 } : { opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: reduced ? 0.15 : 0.4, ease: [0.22, 1, 0.36, 1] }}
        /* Not pinned, at any width. It was `sm:sticky` on the reasoning that the
           most important thing on the page should stay in view — but a card that
           detaches and rides over the content below it reads as a popup, and the
           content it covers is the advice it is telling you to act on. It is the
           first thing on the page; being first is enough. */
        className="min-w-0 overflow-hidden rounded-[var(--radius-card)]"
        style={{
          border: `1px solid ${tone.color}`,
          background: `color-mix(in srgb, ${tone.color} 6%, var(--wx-surface))`,
          boxShadow: 'var(--shadow-glass)',
        }}
      >
        <div className="p-4">
          <div className="mb-2 flex min-w-0 flex-wrap items-center gap-1.5">
            {/* Icon + word, so severity survives greyscale and colour blindness. */}
            <span
              aria-hidden="true"
              className={reduced ? '' : 'pulse-emergency'}
              style={{ color: tone.color, fontSize: '0.85rem' }}
            >
              {tone.icon}
            </span>
            <span
              className="rounded-[var(--radius-pill)] px-2 py-[3px] text-[9.5px] font-bold uppercase tracking-[0.07em]"
              style={{ background: tone.color, color: '#fff' }}
            >
              {t(language, 'emergencyNow')} · {levelLabel(language, emergency.risk_level)}
            </span>
            <span className="min-w-0 truncate text-[11.5px] font-semibold text-ink-soft">
              {hazardLabel(language, emergency.hazard)}
            </span>

            {emergency.is_simulated && (
              <span className="rounded-[var(--radius-pill)] border-2 border-caution bg-caution/20
                               px-2 py-[3px] text-[9.5px] font-bold tracking-wider text-caution-ink">
                {t(language, 'simulatedEmergency')}
              </span>
            )}

            <button
              type="button"
              onClick={() => setDismissed(true)}
              className="ml-auto shrink-0 rounded-[var(--radius-pill)] bg-[rgb(var(--wx-tint)/0.07)]
                         px-2 py-[3px] text-[10px] font-semibold text-ink-soft transition
                         hover:bg-[rgb(var(--wx-tint)/0.14)]"
            >
              {t(language, 'dismissBanner')} ✕
            </button>
          </div>

          <h2 className="text-[15px] font-bold leading-[1.3] tracking-[-0.01em] text-ink">
            {emergency.headline}
          </h2>

          {/* what is happening → why it matters → what to do */}
          <div className="mt-2.5 grid gap-2.5">
            <Block label={t(language, 'whatIsHappening')} body={emergency.what_is_happening} />
            <Block label={t(language, 'whyItMatters')} body={emergency.why_it_matters} />
          </div>

          {emergency.immediate_actions?.length > 0 && (
            <div className="mt-2.5 border-t pt-2.5" style={{ borderColor: `color-mix(in srgb, ${tone.color} 22%, transparent)` }}>
              <p className="wx-eyebrow mb-1.5">{t(language, 'whatToDo')}</p>
              <ol className="space-y-1.5">
                {emergency.immediate_actions.map((action, index) => (
                  <li key={index} className="flex gap-2 text-[12.5px] leading-[1.45] text-ink">
                    <span
                      aria-hidden="true"
                      className="mt-[3px] grid h-[15px] w-[15px] shrink-0 place-items-center rounded-full text-[9px] font-bold"
                      style={{ background: tone.color, color: '#fff' }}
                    >
                      {index + 1}
                    </span>
                    <span className="min-w-0">{action}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          <div className="mt-3 flex min-w-0 flex-wrap items-center gap-2">
            {canSpeak && (
              <button
                type="button"
                onClick={speak}
                className="wx-btn min-w-0 flex-1 text-white transition hover:brightness-110"
                style={{ background: tone.color, borderColor: tone.color }}
              >
                <Icon name={speaking ? 'pause' : 'speaker'} size={14} />
                <span className="min-w-0 truncate">
                  {speaking ? t(language, 'stopInstructions') : t(language, 'listenInstructions')}
                </span>
              </button>
            )}
            {voiceNote && (
              <span role="status" className="w-full text-[10.5px] leading-[1.4] text-muted">
                {voiceNote}
              </span>
            )}
            {until && (
              <span className="text-[10.5px] text-muted">
                {t(language, 'validUntil')} {until}
              </span>
            )}
          </div>
        </div>
      </motion.section>
    </AnimatePresence>
  )
}

function Block({ label, body }) {
  if (!body) return null
  return (
    <div className="min-w-0">
      <p className="wx-eyebrow mb-0.5">{label}</p>
      <p className="text-[12.5px] leading-[1.45] text-ink-soft">{body}</p>
    </div>
  )
}
