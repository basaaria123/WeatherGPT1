import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'
import { Chip, SeverityPill } from './ui/Primitives'

/** BCP-47 voices for the six supported languages. */
const SPEECH_LOCALE = {
  en: 'en-IN', hi: 'hi-IN', te: 'te-IN', bn: 'bn-IN', mr: 'mr-IN', as: 'as-IN',
}

const browserSpeechSupported = () =>
  typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window

/**
 * Can this answer be read aloud at all?
 *
 * Server audio when the backend produced it, otherwise the browser's own
 * synthesiser. `audioAvailable === false` only rules out the server path, which
 * is why it no longer hides the control outright.
 */
const canSpeak = (message, audioAvailable) => {
  if (message.audio_base64 && audioAvailable !== false) return true
  return browserSpeechSupported() && Boolean(message.text?.trim())
}

/**
 * Conversation panel.
 *
 * Sits inside the dashboard rather than taking it over — the reading of the
 * data stays visible while you ask about it. Answers render as plain sentences
 * with actions as a short list, because the same text is what TTS reads aloud.
 */

export default function ChatPanel({
  insight,
  insightLoading,
  messages,
  onSend,
  onVoice,
  pending,
  voicePending,
  error,
  audioAvailable,
  serverTranscribes,
}) {
  const language = useStore((s) => s.language)
  const [draft, setDraft] = useState('')
  const listRef = useRef(null)
  const audioRef = useRef(null)
  const [playingId, setPlayingId] = useState(null)
  const [voiceNote, setVoiceNote] = useState(null)

  const recorder = useVoiceRecorder({ language })
  const quick = t(language, 'quick')

  useEffect(() => {
    // Keep the newest message in view without yanking the whole page.
    const node = listRef.current
    if (node) node.scrollTop = node.scrollHeight
  }, [messages, pending])

  // Leaving the panel must not leave a voice talking.
  useEffect(
    () => () => {
      audioRef.current?.pause()
      if (browserSpeechSupported()) window.speechSynthesis.cancel()
    },
    [],
  )

  const submit = (event) => {
    event?.preventDefault()
    const text = draft.trim()
    if (!text || pending) return
    setDraft('')
    onSend(text)
  }

  // A mis-tap on the microphone produces a blob of a few hundred bytes of
  // container header and no speech. Below this, there is nothing to transcribe.
  const MIN_AUDIO_BYTES = 1200

  // With no speech-to-text on the server, the browser's own transcript is the
  // only thing that can turn this recording into a question. Knowing that up
  // front is what lets us give the real reason instead of a server error about
  // a Python package the user cannot install from a browser.
  const transcriptIsRequired = serverTranscribes === false

  const toggleRecording = async () => {
    if (recorder.recording) {
      const result = await recorder.stop()
      if (!result?.blob) return
      const transcript = result.transcript?.trim() || ''

      if (transcriptIsRequired && !transcript) {
        setVoiceNote(
          result.recognitionRan && !result.recognitionError
            ? 'noSpeech'
            : 'recognitionUnavailable',
        )
        return
      }
      if (!transcript && result.blob.size < MIN_AUDIO_BYTES) {
        // Say so here rather than spending a round trip to be told the same.
        setVoiceNote('noSpeech')
        return
      }
      setVoiceNote(null)
      onVoice(result.blob, transcript)
      return
    }
    setVoiceNote(null)
    await recorder.start()
  }

  const stopSpeaking = () => {
    audioRef.current?.pause()
    audioRef.current = null
    if (browserSpeechSupported()) window.speechSynthesis.cancel()
    setPlayingId(null)
  }

  /**
   * Speak the answer that is on screen.
   *
   * Server-rendered audio is preferred when it exists. When it does not — gTTS
   * needs to reach Google, which a locked-down or serverless host often cannot —
   * the browser's own synthesiser reads the same displayed text rather than the
   * feature quietly disappearing. Either way the spoken words are exactly the
   * words shown, never a UI label.
   */
  const playAudio = (message) => {
    if (playingId === message.id) {
      stopSpeaking()
      return
    }
    stopSpeaking()

    if (message.audio_base64) {
      const audio = new Audio(`data:${message.audio_mime ?? 'audio/mpeg'};base64,${message.audio_base64}`)
      audioRef.current = audio
      audio.onended = () => setPlayingId(null)
      audio.onerror = () => setPlayingId(null)
      audio.play().then(() => setPlayingId(message.id)).catch(() => setPlayingId(null))
      return
    }

    if (!browserSpeechSupported() || !message.text?.trim()) return
    try {
      const utterance = new window.SpeechSynthesisUtterance(message.text)
      utterance.lang = SPEECH_LOCALE[message.lang ?? language] ?? SPEECH_LOCALE.en
      utterance.rate = 0.98
      utterance.onend = () => setPlayingId(null)
      utterance.onerror = () => setPlayingId(null)
      window.speechSynthesis.speak(utterance)
      setPlayingId(message.id)
    } catch {
      setPlayingId(null)
    }
  }

  return (
    <section className="glass flex h-full min-h-[22rem] min-w-0 flex-col p-4 sm:p-5">
      <header className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
          {t(language, 'askAnything')}
        </h2>
        {recorder.recording && (
          <span className="flex items-center gap-1.5 text-[11px] font-medium text-danger">
            <span className="h-1.5 w-1.5 rounded-full bg-danger pulse-alert" />
            {t(language, 'listening')} {recorder.seconds}s
          </span>
        )}
        {/* Transcription runs after the recording stops and can take a few
            seconds. Without this the button just sits there looking broken. */}
        {recorder.transcribing && !recorder.recording && (
          <span className="flex items-center gap-1.5 text-[11px] font-medium text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-[rgb(var(--wx-tint))] pulse-alert" />
            {t(language, 'transcribing')}
          </span>
        )}
      </header>

      <InsightBanner insight={insight} loading={insightLoading} language={language} />

      <div ref={listRef} className="scroll-y -mx-1 min-w-0 flex-1 space-y-3 px-1" aria-live="polite">
        {messages.length === 0 && !pending && !voicePending && (
          <div className="flex flex-col items-center gap-1.5 py-5 text-center">
            <p className="max-w-[32ch] text-[13px] leading-relaxed text-muted">
              {t(language, 'placeholder')}
            </p>
            <p className="max-w-[34ch] text-[11px] leading-relaxed text-faint">
              {t(language, 'askHint')}
            </p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((message) => (
            <Message
              key={message.id}
              message={message}
              onPlay={playAudio}
              playing={playingId === message.id}
              audioAvailable={audioAvailable}
              language={language}
            />
          ))}
        </AnimatePresence>

        {(pending || voicePending) && <TypingIndicator label={t(language, 'thinking')} />}

        {error && (
          <div role="alert" className="rounded-xl border border-danger/25 bg-danger/[0.07] px-3 py-2 text-xs text-ink">
            {error}
          </div>
        )}
      </div>

      {voiceNote && !recorder.error && (
        <p className="mt-2 text-xs text-muted" role="status">
          {t(language, voiceNote)}
        </p>
      )}

      {recorder.error && (
        <p role="alert" className="mt-2 text-[11px] text-caution">
          {recorder.error}
        </p>
      )}

      <div className="mt-3 flex min-w-0 gap-1.5 pb-1 scroll-x">
        {quick.map((label) => (
          <span key={label} className="shrink-0">
            <Chip onClick={() => onSend(label)} disabled={pending}>
              {label}
            </Chip>
          </span>
        ))}
      </div>

      <form onSubmit={submit} className="mt-2.5 flex items-end gap-2">
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) submit(event)
          }}
          rows={1}
          placeholder={t(language, 'placeholder')}
          aria-label={t(language, 'placeholder')}
          disabled={pending}
          className="max-h-28 min-h-[2.75rem] min-w-0 flex-1 resize-none rounded-xl border border-[rgb(var(--wx-tint)/0.12)]
                     bg-[rgb(var(--wx-tint)/0.05)] px-3 py-3 text-sm text-ink placeholder:text-faint
                     focus:border-primary/50 focus:outline-none disabled:opacity-60"
        />

        {recorder.supported && (
          <button
            type="button"
            onClick={toggleRecording}
            disabled={pending || voicePending || recorder.transcribing}
            aria-label={recorder.recording ? t(language, 'stopRecording') : t(language, 'voice')}
            title={recorder.recording ? t(language, 'stopRecording') : t(language, 'voice')}
            className={`relative grid h-11 w-11 shrink-0 place-items-center rounded-xl border transition
                        disabled:opacity-45 ${
                          recorder.recording
                            ? 'border-danger/60 bg-danger/20 text-danger'
                            : 'border-[rgb(var(--wx-tint)/0.12)] bg-[rgb(var(--wx-tint)/0.05)] text-ink-soft hover:border-[rgb(var(--wx-tint)/0.28)] hover:bg-[rgb(var(--wx-tint)/0.1)]'
                        }`}
          >
            {recorder.recording && (
              <motion.span
                className="absolute inset-0 rounded-xl border-2 border-danger"
                animate={{ opacity: [0.7, 0, 0.7], scale: [1, 1.18, 1] }}
                transition={{ duration: 1.6, repeat: Infinity }}
              />
            )}
            <MicIcon />
          </button>
        )}

        <button
          type="submit"
          disabled={pending || !draft.trim()}
          aria-label={t(language, 'send')}
          className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-primary text-lg text-[#04121d]
                     transition hover:brightness-110 disabled:opacity-40"
        >
          ↑
        </button>
      </form>
    </section>
  )
}

function Message({ message, onPlay, playing, audioAvailable, language }) {
  const isUser = message.role === 'user'
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
      className={`flex gap-2 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {!isUser && (
        <span
          aria-hidden="true"
          className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-primary/12 text-[11px] text-primary"
        >
          ◈
        </span>
      )}

      <div className={`max-w-[86%] min-w-0 ${isUser ? 'order-1' : ''}`}>
        <div
          className={`rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
            isUser
              ? 'rounded-br-md bg-primary/15 text-ink'
              : 'rounded-bl-md border border-[rgb(var(--wx-tint)/0.08)] bg-[rgb(var(--wx-tint)/0.05)] text-ink-soft'
          }`}
        >
          {message.transcript && isUser && (
            <p className="mb-1 text-[11px] uppercase tracking-wider text-faint">🎙 {t(language, 'voice')}</p>
          )}
          <p className="whitespace-pre-wrap break-words">{message.text}</p>

          {message.actions?.length > 0 && (
            <ul className="mt-2.5 space-y-1.5 border-t border-[rgb(var(--wx-tint)/0.08)] pt-2.5">
              {message.actions.map((action, index) => (
                <li key={index} className="flex gap-2 text-[13px] text-ink">
                  <span aria-hidden="true" className="mt-[3px] text-primary">▸</span>
                  <span className="min-w-0">{action}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {!isUser && (
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            {message.risk && (
              <SeverityPill level={message.risk.risk_level} score={message.risk.risk_score} compact />
            )}
            {canSpeak(message, audioAvailable) && (
              <button
                type="button"
                onClick={() => onPlay(message)}
                className="rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.10)] bg-[rgb(var(--wx-tint)/0.04)] px-2 py-0.5
                           text-[11px] text-ink-soft transition hover:border-[rgb(var(--wx-tint)/0.25)]"
              >
                {playing ? `◼ ${t(language, 'stopAudio')}` : `▶ ${t(language, 'playAnswer')}`}
              </button>
            )}
            {message.explanation && <WhyDisclosure explanation={message.explanation} language={language} />}
            {message.degradedNote && (
              <span title={message.degradedNote} className="text-[11px] text-faint">
                ⓘ
              </span>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <span
          aria-hidden="true"
          className="order-2 mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-[rgb(var(--wx-tint)/0.07)] text-[11px] text-muted"
        >
          ●
        </span>
      )}
    </motion.div>
  )
}

/** "Why?" is tied to the backend's own explanation field — never re-derived here. */
function WhyDisclosure({ explanation, language }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.10)] bg-[rgb(var(--wx-tint)/0.04)] px-2 py-0.5
                   text-[11px] text-ink-soft transition hover:border-[rgb(var(--wx-tint)/0.25)]"
      >
        {t(language, 'whyThis')} {open ? '▴' : '▾'}
      </button>
      <AnimatePresence>
        {open && (
          <motion.p
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="w-full overflow-hidden rounded-lg border border-[rgb(var(--wx-tint)/0.08)] bg-[rgb(var(--wx-tint)/0.03)] px-2.5 py-2
                       text-[11px] leading-relaxed text-muted"
          >
            {explanation}
          </motion.p>
        )}
      </AnimatePresence>
    </>
  )
}

function TypingIndicator({ label }) {
  return (
    <div className="flex items-center gap-2" role="status">
      <span
        aria-hidden="true"
        className="grid h-7 w-7 place-items-center rounded-lg bg-primary/12 text-[11px] text-primary"
      >
        ◈
      </span>
      <div className="flex items-center gap-2 rounded-2xl rounded-bl-md border border-[rgb(var(--wx-tint)/0.08)] bg-[rgb(var(--wx-tint)/0.05)] px-3.5 py-2.5">
        <span className="flex gap-1" aria-hidden="true">
          {[0, 1, 2].map((index) => (
            <motion.span
              key={index}
              className="h-1.5 w-1.5 rounded-full bg-primary"
              animate={{ opacity: [0.25, 1, 0.25] }}
              transition={{ duration: 1.1, repeat: Infinity, delay: index * 0.18 }}
            />
          ))}
        </span>
        <span className="text-xs text-muted">{label}</span>
      </div>
    </div>
  )
}

function MicIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" />
      <path d="M6 11a6 6 0 0 0 12 0M12 17v4M9 21h6" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
    </svg>
  )
}


/**
 * "What should I know?" answered before anything is asked.
 *
 * The sentences come from /weather/current's insight, which the backend builds
 * from measured values for the selected location and orders by the reader's
 * profile. Nothing here is generated in the browser, so the panel cannot drift
 * from the data the rest of the dashboard is showing.
 */
function InsightBanner({ insight, loading, language }) {
  if (loading && !insight) {
    return (
      <div className="mb-3 rounded-xl border border-[rgb(var(--wx-tint)/0.07)] bg-[rgb(var(--wx-tint)/0.03)] px-3.5 py-3">
        <p className="text-[12px] text-faint">{t(language, 'insightLoading')}</p>
      </div>
    )
  }
  if (!insight?.headline) return null

  const urgent = insight.actionable

  return (
    <motion.div
      key={insight.headline}
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
      className="mb-3 rounded-xl border px-3.5 py-3"
      style={{
        borderColor: urgent ? 'rgb(251 146 60 / 0.42)' : 'rgb(var(--wx-tint) / 0.09)',
        background: urgent ? 'rgb(251 146 60 / 0.09)' : 'rgb(var(--wx-tint) / 0.035)',
      }}
    >
      <p className="text-[14px] font-medium leading-relaxed text-ink">{insight.headline}</p>
      {insight.supporting && (
        <p className="mt-1 text-[12px] leading-relaxed text-ink-soft">{insight.supporting}</p>
      )}
      {insight.factors?.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {insight.factors.map((factor) => (
            <span
              key={factor}
              className="rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.10)] bg-[rgb(var(--wx-tint)/0.05)]
                         px-1.5 py-0.5 text-[11px] text-muted"
            >
              {factor}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  )
}
