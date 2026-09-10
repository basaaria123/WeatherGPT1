import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import { browserSpeechSupported, puterSpeak, utteranceFor } from '../../audio/speech'
import { t } from '../../i18n/ui'
import { useStore } from '../../store/useStore'

/**
 * "Hear this advice" — one control, five states, no surprises.
 *
 *   idle       🔊 Hear this advice
 *   loading    the script is being written and rendered
 *   playing    🔊 Playing…            [ Pause ]   + a progress bar
 *   paused     ▶ Resume
 *   completed  ✓ Advice heard         [ Replay ]
 *   error      Unable to play audio   [ Try again ]
 *
 * Nothing here ever starts on its own. Audio begins on a press and on nothing
 * else — no autoplay on load, on refresh, on an alert arriving, or on the
 * location changing. Changing any of those returns the control to idle and
 * stops whatever was talking, because advice for a place the reader has left
 * is worse than silence.
 *
 * Volume is deliberately absent: an `<audio>` element and the speech synthesiser
 * both play at the device's own volume, and a second volume control inside a
 * page is a control that disagrees with the hardware one.
 *
 * PROVIDERS. Four of them, in one order, and the UI knows about none of it
 * beyond "did that work":
 *
 *   ElevenLabs   the voice the product is meant to have — rendered server-side
 *   Puter        the browser's own hosted voice, no key, tried next
 *   gTTS         the server's fallback, already in hand from the same response
 *   the browser  its native synthesiser, which works with no network at all
 *
 * The server renders what it can and says which provider managed it. When that
 * is not ElevenLabs, Puter is tried before the clip the server sent, because
 * Puter sounds better than gTTS — and because asking the server twice to get
 * that order would cost a round trip on every fallback.
 */

const PROGRESS_STATES = new Set(['playing', 'paused'])

export default function SpokenAdvice({ location, userType }) {
  const language = useStore((s) => s.language)
  const spokenAdvice = useStore((s) => s.spokenAdvice)

  const [state, setState] = useState('idle')
  const [progress, setProgress] = useState(0)
  const [note, setNote] = useState(null)

  const audioRef = useRef(null)
  const scriptRef = useRef(null)

  const stop = useCallback(() => {
    audioRef.current?.pause()
    audioRef.current = null
    if (browserSpeechSupported()) window.speechSynthesis.cancel()
  }, [])

  // Leaving the page, or moving to another place or another reader, must not
  // leave a voice talking about the last one.
  useEffect(() => {
    setState('idle')
    setProgress(0)
    setNote(null)
    scriptRef.current = null
    return stop
  }, [location, userType, language, stop])

  useEffect(() => stop, [stop])

  /** Plays `script` through the browser when the server sent no audio. */
  const speakLocally = useCallback(
    (script) => {
      const utterance = utteranceFor(script, language)
      if (!utterance) return false
      utterance.onend = () => { setState('completed'); setProgress(1) }
      utterance.onerror = () => setState('error')
      // The synthesiser reports no position, so the bar is not drawn for this
      // path rather than animated against a number nobody measured.
      window.speechSynthesis.cancel()
      window.speechSynthesis.speak(utterance)
      setProgress(0)
      setState('playing')
      return true
    },
    [language],
  )

  /** Wires an element into the pause/resume/progress machinery and starts it. */
  const playElement = useCallback((audio) => {
    audioRef.current = audio
    audio.ontimeupdate = () => {
      if (audio.duration) setProgress(audio.currentTime / audio.duration)
    }
    audio.onended = () => { setState('completed'); setProgress(1) }
    audio.onerror = () => setState('error')
    return audio
      .play()
      .then(() => { setState('playing'); return true })
      .catch(() => false)
  }, [])

  const playServerAudio = useCallback(
    (base64, mime) => playElement(new Audio(`data:${mime ?? 'audio/mpeg'};base64,${base64}`)),
    [playElement],
  )

  const start = useCallback(async () => {
    // "Try again" after a half-started attempt must not leave two voices going.
    stop()
    setState('loading')
    setProgress(0)
    setNote(null)
    try {
      const data = await api.spokenAdvice({ location, user_type: userType, language })
      scriptRef.current = data.text
      setNote(data.voice_note ?? null)

      // 1 — ElevenLabs, when the server managed it.
      if (data.audio_base64 && data.audio_provider === 'elevenlabs') {
        if (await playServerAudio(data.audio_base64, data.audio_mime)) return
      }

      // 2 — Puter, ahead of the server's own fallback clip.
      const viaPuter = await puterSpeak(data.text, language)
      if (viaPuter && (await playElement(viaPuter))) return

      // 3 — whatever the server did manage, which by now is gTTS or pyttsx3.
      if (data.audio_base64) {
        if (await playServerAudio(data.audio_base64, data.audio_mime)) return
      }

      // 4 — the browser's own voice. The script still exists either way, so
      // there is something to say right up until there is no way to say it.
      if (!speakLocally(data.text)) setState('error')
    } catch {
      setState('error')
    }
  }, [location, userType, language, playServerAudio, playElement, speakLocally, stop])

  const pause = useCallback(() => {
    if (audioRef.current) audioRef.current.pause()
    else if (browserSpeechSupported()) window.speechSynthesis.pause()
    setState('paused')
  }, [])

  const resume = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.play().then(() => setState('playing')).catch(() => setState('error'))
      return
    }
    if (browserSpeechSupported()) {
      window.speechSynthesis.resume()
      setState('playing')
    }
  }, [])

  const replay = useCallback(() => {
    // The script is already in hand; replaying must not cost a second render.
    const audio = audioRef.current
    if (audio) {
      audio.currentTime = 0
      audio.play().then(() => { setProgress(0); setState('playing') }).catch(() => setState('error'))
      return
    }
    if (scriptRef.current && speakLocally(scriptRef.current)) return
    start()
  }, [speakLocally, start])

  // Off in settings means the control is not offered at all — a toggle that
  // leaves the button on screen is a toggle that did nothing.
  if (!spokenAdvice) return null

  const label = {
    idle: t(language, 'hearAdvice'),
    loading: t(language, 'preparingAudio'),
    playing: t(language, 'audioPlaying'),
    paused: t(language, 'audioPaused'),
    completed: t(language, 'adviceHeard'),
    error: t(language, 'audioFailed'),
  }[state]

  return (
    <div className="mt-3 border-t border-[rgb(var(--wx-tint)/0.09)] pt-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <PrimaryControl
          state={state}
          label={label}
          onStart={start}
          onResume={resume}
          onReplay={replay}
        />

        {state === 'playing' && (
          <SecondaryButton onClick={pause}>{t(language, 'audioPause')}</SecondaryButton>
        )}
        {state === 'completed' && (
          <SecondaryButton onClick={replay}>{t(language, 'audioReplay')}</SecondaryButton>
        )}
        {state === 'error' && (
          <SecondaryButton onClick={start}>{t(language, 'retry')}</SecondaryButton>
        )}

        {/* The state in words, for a reader who cannot see the button change. */}
        <span aria-live="polite" className="sr-only">{label}</span>
      </div>

      {/* A position bar, not a decoration: it only exists while there is a
          position to report, and it does not animate on its own. */}
      {PROGRESS_STATES.has(state) && progress > 0 && (
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(progress * 100)}
          aria-label={t(language, 'audioProgress')}
          className="mt-2 h-[3px] w-full overflow-hidden rounded-full bg-[rgb(var(--wx-tint)/0.10)]"
        >
          <div
            className="h-full rounded-full bg-primary transition-[width] duration-200 ease-linear"
            style={{ width: `${Math.min(100, progress * 100)}%` }}
          />
        </div>
      )}

      {note && <p className="mt-1.5 text-[10.5px] leading-snug text-caution">{note}</p>}
    </div>
  )
}

function PrimaryControl({ state, label, onStart, onResume, onReplay }) {
  const onClick = { idle: onStart, paused: onResume, completed: onReplay, error: onStart }[state]
  const icon = { idle: '🔊', loading: '🔊', playing: '🔊', paused: '▶', completed: '✓', error: '⚠' }[state]
  const busy = state === 'loading' || state === 'playing'

  return (
    <button
      type="button"
      data-testid="hear-advice"
      data-audio-state={state}
      onClick={onClick}
      disabled={busy}
      aria-label={label}
      className={`flex items-center gap-1.5 rounded-[var(--radius-pill)] border px-3 py-1.5 text-[12px]
                  font-medium transition disabled:cursor-default ${
        state === 'error'
          ? 'border-danger/45 bg-danger/10 text-danger'
          : state === 'completed'
            ? 'border-safe/45 bg-safe/10 text-safe'
            : 'border-primary/40 bg-primary/10 text-primary hover:bg-primary/20'
      }`}
    >
      <span aria-hidden="true">{icon}</span>
      <span>{label}</span>
      {state === 'playing' && <Waveform />}
    </button>
  )
}

/**
 * Three bars that move while sound is coming out, and stop when it is not.
 *
 * It exists to answer "is it actually playing?" at a glance, so it is tied to
 * the playing state and to nothing else. It is hidden from assistive tech,
 * which is told the state in words instead, and it is dropped entirely for a
 * reader who has asked for reduced motion.
 */
function Waveform() {
  return (
    <span aria-hidden="true" className="ml-0.5 flex items-end gap-[2px] motion-reduce:hidden">
      {[0, 1, 2].map((bar) => (
        <span
          key={bar}
          className="wx-wave w-[2px] rounded-full bg-current"
          style={{ animationDelay: `${bar * 0.16}s` }}
        />
      ))}
    </span>
  )
}

function SecondaryButton({ onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.15)]
                 bg-[rgb(var(--wx-tint)/0.05)] px-2.5 py-1.5 text-[12px] text-ink-soft transition
                 hover:border-[rgb(var(--wx-tint)/0.30)] hover:bg-[rgb(var(--wx-tint)/0.10)]"
    >
      {children}
    </button>
  )
}
