import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'
import { SPEECH_LOCALE, browserSpeechSupported } from '../audio/speech'
import { Chip, SeverityPill } from './ui/Primitives'
import Icon from './ui/Icon'

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
  suggestions,
}) {
  const language = useStore((s) => s.language)
  const voiceQuestions = useStore((s) => s.voiceQuestions)
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

  const greeting = messages.length === 0 && !pending && !voicePending

  return (
    /* No card around the conversation. The reference puts the bubbles straight
       on the page — a chat inside a bordered panel inside a phone frame is
       three nested containers for one thread. */
    <section className="flex min-h-[calc(100dvh-16rem)] min-w-0 flex-col">
      <InsightBanner insight={insight} loading={insightLoading} language={language} />

      <div ref={listRef} className="scroll-y -mx-1 min-w-0 flex-1 space-y-3 px-1 pt-0.5" aria-live="polite">
        {/* The opening turn is a message, not an empty state: the assistant
            introduces itself and offers the reader's own questions, which is
            exactly what the reference's first screen shows. */}
        {greeting && (
          <Bubble>
            <p className="text-[12.5px] leading-[1.5] text-ink-soft">{t(language, 'chatGreeting')}</p>
            {suggestions?.length > 0 && (
              <>
                <p className="mt-2.5 text-[11.5px] font-semibold text-ink">{t(language, 'chatSuggestLead')}</p>
                <ul className="mt-1.5 space-y-1.5">
                  {suggestions.slice(0, 4).map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        onClick={() => onSend(item.query)}
                        disabled={pending}
                        className="flex w-full min-w-0 items-center gap-1.5 rounded-[var(--radius-pill)]
                                   border border-[rgb(var(--wx-tint)/0.22)] bg-[var(--wx-surface)]
                                   px-2.5 py-1.5 text-left text-[11.5px] font-medium text-primary
                                   transition hover:bg-[rgb(var(--wx-tint)/0.06)] disabled:opacity-50"
                      >
                        <Icon name="sparkle" size={12} />
                        <span className="min-w-0 truncate">{item.label}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </Bubble>
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
          <div
            role="alert"
            className="rounded-[var(--radius-control)] border border-danger/30 bg-danger/[0.06] px-3 py-2
                       text-[12px] leading-[1.45] text-ink"
          >
            {error}
          </div>
        )}
      </div>

      {/* --- Recording state, said in words ------------------------------- */}
      {(recorder.recording || (voicePending && !recorder.recording)) && (
        <p className="mt-2 flex items-center gap-1.5 px-1 text-[11px] font-semibold text-danger" role="status">
          <span className="h-1.5 w-1.5 rounded-full bg-current pulse-alert" />
          {recorder.recording
            ? `${t(language, 'listening')} ${recorder.seconds}s`
            : t(language, 'transcribing')}
        </p>
      )}

      {voiceNote && !recorder.error && (
        <p className="mt-2 px-1 text-[11px] text-muted" role="status">{t(language, voiceNote)}</p>
      )}

      {recorder.error && (
        <p role="alert" className="mt-2 px-1 text-[11px] text-caution-ink">{recorder.error}</p>
      )}

      {/* The stock openers, kept below the thread where they do not compete
          with the reader's own suggested questions above it. */}
      {greeting && (
        <div className="scroll-x mt-3 flex min-w-0 gap-1.5 pb-1">
          {quick.map((label) => (
            <span key={label} className="shrink-0">
              <Chip onClick={() => onSend(label)} disabled={pending}>{label}</Chip>
            </span>
          ))}
        </div>
      )}

      {/* --- Composer ----------------------------------------------------- */}
      <form onSubmit={submit} className="mt-3 flex min-w-0 items-end gap-1.5">
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) submit(event)
          }}
          rows={1}
          placeholder={t(language, 'typeMessage')}
          aria-label={t(language, 'typeMessage')}
          disabled={pending}
          className="wx-field max-h-28 min-h-[2.4rem] min-w-0 flex-1 resize-none py-[9px] disabled:opacity-60"
        />

        {recorder.supported && voiceQuestions && (
          <button
            type="button"
            onClick={toggleRecording}
            disabled={pending || voicePending}
            aria-label={recorder.recording ? t(language, 'stopRecording') : t(language, 'voice')}
            title={recorder.recording ? t(language, 'stopRecording') : t(language, 'voice')}
            className={`relative grid h-[38px] w-[38px] shrink-0 place-items-center rounded-full border transition
                        disabled:opacity-45 ${
                          recorder.recording
                            ? 'border-danger bg-danger/15 text-danger'
                            : 'border-[var(--wx-border)] bg-[var(--wx-surface)] text-ink-soft hover:border-primary/50 hover:text-primary'
                        }`}
          >
            {recorder.recording && (
              <motion.span
                className="absolute inset-0 rounded-full border-2 border-danger"
                animate={{ opacity: [0.7, 0, 0.7], scale: [1, 1.18, 1] }}
                transition={{ duration: 1.6, repeat: Infinity }}
              />
            )}
            <Icon name="mic" size={16} />
          </button>
        )}

        <button
          type="submit"
          disabled={pending || !draft.trim()}
          aria-label={t(language, 'send')}
          className="grid h-[38px] w-[38px] shrink-0 place-items-center rounded-full bg-primary text-white
                     transition hover:brightness-110 disabled:opacity-40"
        >
          <Icon name="send" size={16} />
        </button>
      </form>
    </section>
  )
}

/**
 * The assistant's side of the conversation: a white card with a hairline blue
 * edge and its avatar outside it, exactly as the reference draws it.
 */
function Bubble({ children, className = '' }) {
  return (
    <div className="flex min-w-0 gap-2">
      <span
        aria-hidden="true"
        className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-primary text-white"
      >
        <Icon name="cloud" size={15} stroke={1.9} />
      </span>
      <div
        className={`min-w-0 max-w-[88%] rounded-[var(--radius-card)] rounded-tl-md border
                    border-[rgb(var(--wx-tint)/0.18)] bg-[var(--wx-surface)] px-3 py-2.5
                    shadow-[var(--shadow-glass)] ${className}`}
      >
        {children}
      </div>
    </div>
  )
}

function Message({ message, onPlay, playing, audioAvailable, language }) {
  const isUser = message.role === 'user'

  // The reader's own turn: a solid blue bubble on the right, white text, with
  // the time beneath it. No avatar — the reference gives one only to the
  // assistant, and a second one would double the gutter on a 390px screen.
  if (isUser) {
    return (
      <motion.div
        layout
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
        className="flex min-w-0 flex-col items-end"
      >
        <div className="min-w-0 max-w-[82%] rounded-[var(--radius-card)] rounded-br-md bg-primary px-3 py-2">
          {message.transcript && (
            <p className="mb-1 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.07em] text-white/75">
              <Icon name="mic" size={10} />
              {t(language, 'voice')}
            </p>
          )}
          <p className="whitespace-pre-wrap break-words text-[12.5px] leading-[1.5] text-white">
            {message.text}
          </p>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
      className="min-w-0"
    >
      <Bubble>
        <p className="whitespace-pre-wrap break-words text-[12.5px] leading-[1.5] text-ink-soft">
          {message.text}
        </p>

        {message.actions?.length > 0 && (
          <ul className="mt-2.5 space-y-1.5 border-t border-[var(--wx-border)] pt-2.5">
            {message.actions.map((action, index) => (
              <li key={index} className="flex gap-2 text-[12px] leading-[1.45] text-ink">
                <span aria-hidden="true" className="mt-[5px] h-1 w-1 shrink-0 rounded-full bg-primary" />
                <span className="min-w-0">{action}</span>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-2 flex min-w-0 flex-wrap items-center gap-1.5">
          {message.risk && (
            <SeverityPill level={message.risk.risk_level} score={message.risk.risk_score} compact />
          )}
          {canSpeak(message, audioAvailable) && (
            <button
              type="button"
              onClick={() => onPlay(message)}
              className="inline-flex items-center gap-1 rounded-[var(--radius-pill)] bg-[rgb(var(--wx-tint)/0.08)]
                         px-2 py-0.5 text-[10.5px] font-semibold text-primary transition
                         hover:bg-[rgb(var(--wx-tint)/0.16)]"
            >
              <Icon name={playing ? 'pause' : 'speaker'} size={11} />
              {playing ? t(language, 'stopAudio') : t(language, 'playAnswer')}
            </button>
          )}
          {message.explanation && <WhyDisclosure explanation={message.explanation} language={language} />}
          {message.degradedNote && (
            <span title={message.degradedNote} className="text-faint">
              <Icon name="info" size={12} />
            </span>
          )}
        </div>
      </Bubble>
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
        className="inline-flex items-center gap-1 rounded-[var(--radius-pill)] bg-[rgb(var(--wx-tint)/0.07)]
                   px-2 py-0.5 text-[10.5px] font-semibold text-ink-soft transition
                   hover:bg-[rgb(var(--wx-tint)/0.14)]"
      >
        {t(language, 'whyThis')}
        <Icon name="chevronDown" size={10} className={open ? 'rotate-180' : ''} />
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
        className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-primary text-white"
      >
        <Icon name="cloud" size={15} stroke={1.9} />
      </span>
      <div className="flex items-center gap-2 rounded-[var(--radius-card)] rounded-tl-md border border-[rgb(var(--wx-tint)/0.18)] bg-[var(--wx-surface)] px-3 py-2.5">
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

function InsightBanner({ insight, loading, language }) {
  if (loading && !insight) {
    return (
      <div className="glass mb-3 min-w-0 px-3.5 py-3">
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
      className="wx-note mb-3 min-w-0 p-3.5"
      style={{
        '--wx-note-line': urgent
          ? 'color-mix(in srgb, var(--color-warning) 34%, transparent)'
          : 'var(--wx-border)',
        '--wx-note-fill': urgent
          ? 'color-mix(in srgb, var(--color-warning) 6%, #fff)'
          : 'var(--wx-surface)',
      }}
    >
      <p className="text-[13px] font-semibold leading-[1.45] text-ink">{insight.headline}</p>
      {insight.supporting && (
        <p className="mt-1 text-[12px] leading-[1.45] text-ink-soft">{insight.supporting}</p>
      )}
      {insight.factors?.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {insight.factors.map((factor) => (
            <span
              key={factor}
              className="rounded-[var(--radius-pill)] bg-[rgb(var(--wx-tint)/0.07)] px-1.5 py-0.5
                         text-[10.5px] font-medium text-muted"
            >
              {factor}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  )
}
