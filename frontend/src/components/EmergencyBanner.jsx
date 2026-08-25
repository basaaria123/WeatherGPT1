import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { hazardLabel, t } from '../i18n/ui'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { useStore } from '../store/useStore'
import { severityOf } from './ui/severity'

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

const SPEECH_LOCALE = { en: 'en-IN', hi: 'hi-IN', te: 'te-IN', bn: 'bn-IN', mr: 'mr-IN', as: 'as-IN' }
const speechSupported = () =>
  typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window

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
  const reduced = useReducedMotion()
  const [dismissed, setDismissed] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const audioRef = useRef(null)

  const active = Boolean(emergency?.active)
  const hazard = emergency?.hazard

  // A new hazard, or a fresh activation, brings the banner back.
  useEffect(() => {
    if (active) setDismissed(false)
  }, [active, hazard])

  const stop = () => {
    audioRef.current?.pause()
    audioRef.current = null
    if (speechSupported()) window.speechSynthesis.cancel()
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
    const text = emergency.spoken_instructions || emergency.headline
    if (!text) return

    if (audioBase64) {
      const audio = new Audio(`data:${audioMime ?? 'audio/mpeg'};base64,${audioBase64}`)
      audioRef.current = audio
      audio.onended = () => setSpeaking(false)
      audio.onerror = () => setSpeaking(false)
      audio.play().then(() => setSpeaking(true)).catch(() => setSpeaking(false))
      return
    }
    if (!speechSupported()) return
    try {
      const utterance = new window.SpeechSynthesisUtterance(text)
      utterance.lang = SPEECH_LOCALE[language] ?? SPEECH_LOCALE.en
      utterance.rate = 0.98
      utterance.onend = () => setSpeaking(false)
      utterance.onerror = () => setSpeaking(false)
      window.speechSynthesis.speak(utterance)
      setSpeaking(true)
    } catch {
      setSpeaking(false)
    }
  }

  const canSpeak = Boolean(audioBase64) || speechSupported()

  // Dismissed does not mean resolved: a compact indicator stays while the risk
  // does, so a cleared banner can never read as an all-clear.
  if (dismissed) {
    return (
      <div
        role="status"
        className="sticky top-[3.25rem] z-20 mb-2 flex items-center gap-2 rounded-xl border px-3 py-1.5"
        style={{ borderColor: tone.ring, background: tone.tint }}
      >
        <span aria-hidden="true" style={{ color: tone.color }}>{tone.icon}</span>
        <span className="text-[12px] font-semibold text-ink">{t(language, 'stillActive')}</span>
        <span className="text-[12px] text-muted">· {hazardLabel(language, emergency.hazard)}</span>
        <button
          type="button"
          onClick={() => setDismissed(false)}
          className="ml-auto rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.18)]
                     px-2 py-0.5 text-[11px] text-ink-soft transition hover:border-[rgb(var(--wx-tint)/0.35)]"
        >
          {t(language, 'emergencyNow')} →
        </button>
      </div>
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
        className="sticky top-[3.25rem] z-20 mb-3 overflow-hidden rounded-2xl border-2"
        style={{ borderColor: tone.color, background: tone.tint }}
      >
        <div className="p-4 sm:p-5">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            {/* Icon + word, so severity survives greyscale and colour blindness. */}
            <span
              aria-hidden="true"
              className={reduced ? '' : 'pulse-emergency'}
              style={{ color: tone.color, fontSize: '1.1rem' }}
            >
              {tone.icon}
            </span>
            <span
              className="rounded-[var(--radius-pill)] px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider"
              style={{ background: tone.color, color: '#fff' }}
            >
              {t(language, 'emergencyNow')} · {emergency.risk_level}
            </span>
            <span className="text-[13px] font-semibold text-ink">
              {hazardLabel(language, emergency.hazard)}
            </span>

            {emergency.is_simulated && (
              <span className="rounded-[var(--radius-pill)] border-2 border-caution bg-caution/20
                               px-2 py-0.5 text-[11px] font-bold tracking-wider text-caution">
                {t(language, 'simulatedEmergency')}
              </span>
            )}

            <button
              type="button"
              onClick={() => setDismissed(true)}
              className="ml-auto rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.2)]
                         px-2.5 py-1 text-[11px] text-ink-soft transition
                         hover:border-[rgb(var(--wx-tint)/0.4)]"
            >
              {t(language, 'dismissBanner')} ✕
            </button>
          </div>

          <h2 className="text-[17px] font-semibold leading-snug text-ink sm:text-lg">
            {emergency.headline}
          </h2>

          {/* what is happening → why it matters → what to do */}
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <Block label={t(language, 'whatIsHappening')} body={emergency.what_is_happening} />
            <Block label={t(language, 'whyItMatters')} body={emergency.why_it_matters} />
          </div>

          {emergency.immediate_actions?.length > 0 && (
            <div className="mt-3 border-t border-[rgb(var(--wx-tint)/0.14)] pt-3">
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
                {t(language, 'whatToDo')}
              </p>
              <ol className="space-y-1.5">
                {emergency.immediate_actions.map((action, index) => (
                  <li key={index} className="flex gap-2 text-[13px] leading-relaxed text-ink">
                    <span
                      aria-hidden="true"
                      className="mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded-full text-[10px] font-bold"
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

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {canSpeak && (
              <button
                type="button"
                onClick={speak}
                className="rounded-[var(--radius-pill)] px-3.5 py-2 text-[12px] font-semibold text-white transition
                           hover:brightness-110 focus-visible:outline-offset-2"
                style={{ background: tone.color }}
              >
                {speaking ? `◼ ${t(language, 'stopInstructions')}` : `🔊 ${t(language, 'listenInstructions')}`}
              </button>
            )}
            {until && (
              <span className="text-[11px] text-muted">
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
    <div>
      <p className="mb-0.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{label}</p>
      <p className="text-[13px] leading-relaxed text-ink-soft">{body}</p>
    </div>
  )
}
