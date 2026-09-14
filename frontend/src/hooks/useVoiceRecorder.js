import { useCallback, useEffect, useRef, useState } from 'react'
import { speechTagFor } from '../i18n/languages'

/**
 * Microphone capture, as a click-to-toggle recorder.
 *
 * One click starts, the next stops. There is no press-and-hold path here and
 * never has been: the button that drives this binds `onClick` and nothing else.
 *
 * Two transcribers run against one recording. The browser's own
 * SpeechRecognition listens live, for free, with no round trip; the audio blob
 * goes to the server afterwards, where Deepgram is the first provider in the
 * chain. The server's answer wins when it arrives — it is the better recogniser
 * and it is the one that works in browsers with no Web Speech API at all — and
 * the browser's transcript is what makes the feature work when the server has
 * no speech provider configured.
 *
 * WHAT THIS FILE IS CAREFUL ABOUT, and why each one is here rather than
 * obvious: every item below was a way for the microphone to end up stuck on, or
 * for two microphones to end up running at once.
 *
 *   - A second `start()` before the first finished opened a second stream and a
 *     second MediaRecorder. The first was then unreachable and kept the
 *     microphone light on until the tab closed. `busyRef` is checked and set
 *     synchronously, because React state updates are not.
 *   - `stop()` resolved from the recorder's `onstop`. If that never fired —
 *     a codec error, a revoked device — the promise never settled and the
 *     interface sat on "Transcribing…" forever. It is now raced against a
 *     timeout that resolves with whatever chunks exist.
 *   - The cleanup path stopped the *stream* but not the *recorder*, so
 *     unmounting mid-recording left a recorder running against dead tracks.
 *   - `recorderRef` was never cleared, so a stale recorder from a previous
 *     session could be asked for its state.
 *   - The duration cap called `recorder.stop()` from inside a `setState`
 *     updater — a side effect in a function React may call twice.
 */

// Long enough for a real question asked at a natural pace. The previous cap was
// twenty seconds, which cut the end off exactly the long sentences a recogniser
// is most useful for.
const MAX_SECONDS = 90

// How long to wait for `onstop` before giving up on it and using the chunks in
// hand. Generous, because a large blob can take a moment to assemble.
const STOP_TIMEOUT_MS = 4000

export function useVoiceRecorder({ language = 'en' } = {}) {
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState(null)
  const [seconds, setSeconds] = useState(0)

  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)
  const resolveRef = useRef(null)
  const tickRef = useRef(null)
  const stopTimerRef = useRef(null)
  const recognitionRef = useRef(null)
  const transcriptRef = useRef('')
  const recognitionErrorRef = useRef(null)
  const recognitionStartedRef = useRef(false)
  // Set synchronously so a double-click cannot open two microphones. React
  // state cannot do this job: `recording` is still false on the second click of
  // a fast double-click, because the re-render has not happened yet.
  const busyRef = useRef(false)
  const mountedRef = useRef(true)

  const recognitionSupported =
    typeof window !== 'undefined' &&
    Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)

  const supported =
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof window !== 'undefined' &&
    typeof window.MediaRecorder !== 'undefined'

  /** Release every device resource. Safe to call more than once. */
  const releaseDevice = useCallback(() => {
    if (tickRef.current) clearInterval(tickRef.current)
    tickRef.current = null
    if (stopTimerRef.current) clearTimeout(stopTimerRef.current)
    stopTimerRef.current = null

    // The recorder first: stopping the tracks underneath a running recorder is
    // what produced "Failed to execute 'stop'" in the console.
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      try {
        recorder.stop()
      } catch {
        /* already stopping */
      }
    }
    recorderRef.current = null

    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null

    try {
      recognitionRef.current?.stop()
    } catch {
      /* recognition may already be stopped */
    }
    recognitionRef.current = null
    busyRef.current = false
  }, [])

  // Leaving the page mid-recording must not leave the microphone open, and must
  // not set state on a component that is gone.
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      resolveRef.current = null
      releaseDevice()
    }
  }, [releaseDevice])

  const startRecognition = useCallback(() => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!Recognition) return
    try {
      const recognition = new Recognition()
      // BCP-47 tags; the browser ignores an unknown one rather than failing.
      recognition.lang = speechTagFor(language)
      recognition.interimResults = false
      // `continuous` matters for a toggle recorder: without it the recogniser
      // stops at the first pause, so a sentence with a breath in the middle came
      // back as its first clause.
      recognition.continuous = true
      recognition.onresult = (event) => {
        transcriptRef.current = Array.from(event.results)
          .map((result) => result[0]?.transcript ?? '')
          .join(' ')
          .replace(/\s+/g, ' ')
          .trim()
      }
      // Not a bonus: on a server with no speech-to-text configured this
      // transcript is the only thing that makes the microphone work. So record
      // why it failed instead of discarding it — the caller uses this to tell
      // the reader to type rather than leaving them with a server error.
      recognition.onerror = (event) => {
        recognitionErrorRef.current = event?.error || 'unknown'
      }
      recognition.start()
      recognitionRef.current = recognition
      recognitionStartedRef.current = true
    } catch {
      recognitionErrorRef.current = 'start-failed'
    }
  }, [language])

  /** Hand the recording to whoever is waiting on `stop()`, exactly once. */
  const settle = useCallback((recorder) => {
    if (stopTimerRef.current) clearTimeout(stopTimerRef.current)
    stopTimerRef.current = null
    const resolve = resolveRef.current
    resolveRef.current = null

    const blob = new Blob(chunksRef.current, {
      type: recorder?.mimeType || chunksRef.current[0]?.type || 'audio/webm',
    })
    chunksRef.current = []
    releaseDevice()

    if (mountedRef.current) {
      setRecording(false)
      setSeconds(0)
    }

    const heard = transcriptRef.current?.trim()
    resolve?.({
      blob,
      transcript: heard || '',
      transcriptSource: heard ? 'browser' : 'none',
      // So the caller can distinguish "said nothing" from "the browser could
      // not listen at all", which need different advice.
      recognitionError: recognitionErrorRef.current,
      recognitionRan: recognitionStartedRef.current,
    })
  }, [releaseDevice])

  const start = useCallback(async () => {
    // Checked and set before the first `await`, so two clicks in the same tick
    // cannot both get past here.
    if (busyRef.current) return false
    busyRef.current = true

    setError(null)
    transcriptRef.current = ''
    recognitionErrorRef.current = null
    recognitionStartedRef.current = false
    chunksRef.current = []

    if (!supported) {
      busyRef.current = false
      setError('Voice recording is not supported in this browser. Please type your question.')
      return false
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      // Unmounted while the permission prompt was open: take the microphone
      // back rather than leaving it live behind a screen nobody is looking at.
      if (!mountedRef.current) {
        stream.getTracks().forEach((track) => track.stop())
        busyRef.current = false
        return false
      }
      streamRef.current = stream

      // Not every browser records the same container. Safari has no webm at
      // all, so forcing one throws at construction time and the microphone
      // never starts — which is what "it does nothing on iPhone" was.
      const mimeType = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
        'audio/aac',
      ].find((type) => window.MediaRecorder.isTypeSupported?.(type))

      const recorder = new window.MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      recorder.ondataavailable = (event) => {
        if (event.data?.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = () => settle(recorder)
      recorder.onerror = () => {
        setError('The recording stopped unexpectedly. Please try again, or type your question.')
        settle(recorder)
      }

      // A timeslice, so chunks arrive during the recording rather than only at
      // the end. If `onstop` never fires, what has already arrived is still a
      // usable recording instead of an empty blob.
      recorder.start(1000)
      recorderRef.current = recorder
      startRecognition()
      setRecording(true)
      setSeconds(0)

      tickRef.current = setInterval(() => {
        // The cap is enforced here, outside the state updater. Calling
        // `recorder.stop()` from inside `setSeconds` put a side effect in a
        // function React is allowed to invoke twice.
        setSeconds((value) => value + 1)
      }, 1000)
      return true
    } catch (err) {
      releaseDevice()
      if (mountedRef.current) {
        setRecording(false)
        setError(microphoneMessage(err))
      }
      return false
    }
  }, [supported, releaseDevice, settle, startRecognition])

  // The duration cap, as an effect on the tick rather than inside it.
  useEffect(() => {
    if (!recording || seconds < MAX_SECONDS) return
    const recorder = recorderRef.current
    if (recorder && recorder.state === 'recording') {
      try {
        recorder.stop()
      } catch {
        /* already stopping */
      }
    }
  }, [recording, seconds])

  const stop = useCallback(
    () =>
      new Promise((resolve) => {
        const recorder = recorderRef.current
        if (!recorder || recorder.state === 'inactive') {
          releaseDevice()
          if (mountedRef.current) {
            setRecording(false)
            setSeconds(0)
          }
          resolve(null)
          return
        }
        resolveRef.current = resolve

        // `onstop` is the normal path. This is the one that stops the interface
        // hanging on "Transcribing…" when it does not come.
        stopTimerRef.current = setTimeout(() => settle(recorder), STOP_TIMEOUT_MS)

        try {
          recorder.stop()
        } catch {
          settle(recorder)
        }
      }),
    [releaseDevice, settle],
  )

  /** Throw the recording away and release the microphone. */
  const cancel = useCallback(() => {
    const recorder = recorderRef.current
    resolveRef.current = null
    if (recorder) recorder.onstop = null
    chunksRef.current = []
    releaseDevice()
    if (mountedRef.current) {
      setRecording(false)
      setSeconds(0)
    }
  }, [releaseDevice])

  return {
    supported,
    recognitionSupported,
    recording,
    seconds,
    error,
    start,
    stop,
    cancel,
    maxSeconds: MAX_SECONDS,
  }
}

/**
 * Why the microphone would not open, in words a reader can act on.
 *
 * `getUserMedia` distinguishes these and the interface did not, so "another app
 * is using your microphone" and "you denied permission" both arrived as one
 * sentence telling the reader to type instead — advice that is useless for the
 * first and unnecessary for the second.
 */
function microphoneMessage(err) {
  switch (err?.name) {
    case 'NotAllowedError':
    case 'SecurityError':
      return 'Microphone access was blocked. Allow it in your browser settings, or type your question instead.'
    case 'NotFoundError':
    case 'OverconstrainedError':
      return 'No microphone was found on this device. Please type your question instead.'
    case 'NotReadableError':
    case 'AbortError':
      return 'The microphone is in use by another application. Close it and try again, or type your question.'
    default:
      return 'Could not start the microphone. Please type your question instead.'
  }
}
