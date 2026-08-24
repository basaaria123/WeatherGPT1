import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'
import { Chip, SeverityPill } from './ui/Primitives'

/**
 * Conversation panel.
 *
 * Sits inside the dashboard rather than taking it over — the reading of the
 * data stays visible while you ask about it. Answers render as plain sentences
 * with actions as a short list, because the same text is what TTS reads aloud.
 */

export default function ChatPanel({
  messages,
  onSend,
  onVoice,
  pending,
  voicePending,
  error,
  audioAvailable,
}) {
  const language = useStore((s) => s.language)
  const [draft, setDraft] = useState('')
  const listRef = useRef(null)
  const audioRef = useRef(null)
  const [playingId, setPlayingId] = useState(null)

  const recorder = useVoiceRecorder({ language })
  const quick = t(language, 'quick')

  useEffect(() => {
    // Keep the newest message in view without yanking the whole page.
    const node = listRef.current
    if (node) node.scrollTop = node.scrollHeight
  }, [messages, pending])

  useEffect(() => () => audioRef.current?.pause(), [])

  const submit = (event) => {
    event?.preventDefault()
    const text = draft.trim()
    if (!text || pending) return
    setDraft('')
    onSend(text)
  }

  const toggleRecording = async () => {
    if (recorder.recording) {
      const result = await recorder.stop()
      if (result?.blob) onVoice(result.blob, result.transcript)
      return
    }
    await recorder.start()
  }

  const playAudio = (message) => {
    if (!message.audio_base64) return
    if (playingId === message.id) {
      audioRef.current?.pause()
      setPlayingId(null)
      return
    }
    audioRef.current?.pause()
    const audio = new Audio(`data:${message.audio_mime ?? 'audio/mpeg'};base64,${message.audio_base64}`)
    audioRef.current = audio
    audio.onended = () => setPlayingId(null)
    audio.onerror = () => setPlayingId(null)
    audio.play().then(() => setPlayingId(message.id)).catch(() => setPlayingId(null))
  }

  return (
    <section className="glass flex h-full min-h-[26rem] min-w-0 flex-col p-4 sm:p-5">
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
      </header>

      <div ref={listRef} className="scroll-y -mx-1 min-w-0 flex-1 space-y-3 px-1" aria-live="polite">
        {messages.length === 0 && !pending && !voicePending && (
          <div className="flex h-full flex-col items-center justify-center gap-2 py-8 text-center">
            <span aria-hidden="true" className="text-2xl text-primary/70">◈</span>
            <p className="max-w-[30ch] text-xs leading-relaxed text-muted">
              {t(language, 'placeholder')}
            </p>
            <p className="max-w-[32ch] text-[11px] leading-relaxed text-faint">
              Ask in any supported language, or tap the microphone.
            </p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((message) => (
            <Message key={message.id} message={message} onPlay={playAudio} playing={playingId === message.id} audioAvailable={audioAvailable} language={language} />
          ))}
        </AnimatePresence>

        {(pending || voicePending) && <TypingIndicator label={t(language, 'thinking')} />}

        {error && (
          <div role="alert" className="rounded-xl border border-danger/25 bg-danger/[0.07] px-3 py-2 text-xs text-ink">
            {error}
          </div>
        )}
      </div>

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
          className="max-h-28 min-h-[2.75rem] min-w-0 flex-1 resize-none rounded-xl border border-white/12
                     bg-white/[0.05] px-3 py-3 text-sm text-ink placeholder:text-faint
                     focus:border-primary/50 focus:outline-none disabled:opacity-60"
        />

        {recorder.supported && (
          <button
            type="button"
            onClick={toggleRecording}
            disabled={pending || voicePending}
            aria-label={recorder.recording ? t(language, 'stopRecording') : t(language, 'voice')}
            title={recorder.recording ? t(language, 'stopRecording') : t(language, 'voice')}
            className={`relative grid h-11 w-11 shrink-0 place-items-center rounded-xl border transition
                        disabled:opacity-45 ${
                          recorder.recording
                            ? 'border-danger/60 bg-danger/20 text-danger'
                            : 'border-white/12 bg-white/[0.05] text-ink-soft hover:border-white/28 hover:bg-white/[0.1]'
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
              : 'rounded-bl-md border border-white/[0.08] bg-white/[0.05] text-ink-soft'
          }`}
        >
          {message.transcript && isUser && (
            <p className="mb-1 text-[10px] uppercase tracking-wider text-faint">🎙 {t(language, 'voice')}</p>
          )}
          <p className="whitespace-pre-wrap break-words">{message.text}</p>

          {message.actions?.length > 0 && (
            <ul className="mt-2.5 space-y-1.5 border-t border-white/[0.08] pt-2.5">
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
            {message.audio_base64 && audioAvailable !== false && (
              <button
                type="button"
                onClick={() => onPlay(message)}
                className="rounded-[var(--radius-pill)] border border-white/10 bg-white/[0.04] px-2 py-0.5
                           text-[10px] text-ink-soft transition hover:border-white/25"
              >
                {playing ? `◼ ${t(language, 'stopAudio')}` : `▶ ${t(language, 'playAnswer')}`}
              </button>
            )}
            {message.explanation && <WhyDisclosure explanation={message.explanation} language={language} />}
            {message.degradedNote && (
              <span title={message.degradedNote} className="text-[10px] text-faint">
                ⓘ
              </span>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <span
          aria-hidden="true"
          className="order-2 mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white/[0.07] text-[11px] text-muted"
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
        className="rounded-[var(--radius-pill)] border border-white/10 bg-white/[0.04] px-2 py-0.5
                   text-[10px] text-ink-soft transition hover:border-white/25"
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
            className="w-full overflow-hidden rounded-lg border border-white/[0.08] bg-white/[0.03] px-2.5 py-2
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
      <div className="flex items-center gap-2 rounded-2xl rounded-bl-md border border-white/[0.08] bg-white/[0.05] px-3.5 py-2.5">
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
