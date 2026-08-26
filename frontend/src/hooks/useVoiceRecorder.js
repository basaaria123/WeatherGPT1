import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Microphone capture for /voice-chat.
 *
 * Also opportunistically runs the browser's own SpeechRecognition when it
 * exists. That transcript is sent alongside the audio as `client_transcript`,
 * which the backend uses only if server-side Whisper is unavailable — so voice
 * still works on a deployment without the Whisper model installed.
 */
const MAX_SECONDS = 20

export function useVoiceRecorder({ language = 'en' } = {}) {
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState(null)
  const [seconds, setSeconds] = useState(0)

  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)
  const resolveRef = useRef(null)
  const tickRef = useRef(null)
  const recognitionRef = useRef(null)
  const transcriptRef = useRef('')
  const recognitionErrorRef = useRef(null)
  const recognitionStartedRef = useRef(false)

  const recognitionSupported =
    typeof window !== 'undefined' &&
    Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)

  const supported =
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof window !== 'undefined' &&
    typeof window.MediaRecorder !== 'undefined'

  const cleanup = useCallback(() => {
    if (tickRef.current) clearInterval(tickRef.current)
    tickRef.current = null
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    try {
      recognitionRef.current?.stop()
    } catch {
      /* recognition may already be stopped */
    }
    recognitionRef.current = null
  }, [])

  useEffect(() => cleanup, [cleanup])

  const startRecognition = useCallback(() => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!Recognition) return
    try {
      const recognition = new Recognition()
      // BCP-47 tags; the browser ignores an unknown one rather than failing.
      recognition.lang = { en: 'en-IN', hi: 'hi-IN', te: 'te-IN', bn: 'bn-IN', mr: 'mr-IN', as: 'as-IN' }[language] ?? 'en-IN'
      recognition.interimResults = false
      recognition.continuous = false
      recognition.onresult = (event) => {
        transcriptRef.current = Array.from(event.results)
          .map((result) => result[0]?.transcript ?? '')
          .join(' ')
          .trim()
      }
      // Not a bonus any more: on a server with no speech-to-text configured,
      // this transcript is the only thing that makes the microphone work. So
      // record why it failed instead of discarding it — the caller uses this
      // to tell the user to type rather than leaving them with a server error
      // about a Python package they cannot install from a browser.
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

  const start = useCallback(async () => {
    setError(null)
    transcriptRef.current = ''
    recognitionErrorRef.current = null
    recognitionStartedRef.current = false
    if (!supported) {
      setError('Voice recording is not supported in this browser. Please type your question.')
      return false
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg']
        .find((type) => window.MediaRecorder.isTypeSupported?.(type))

      const recorder = new window.MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      chunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data?.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        cleanup()
        setRecording(false)
        setSeconds(0)
        resolveRef.current?.({
          blob,
          transcript: transcriptRef.current,
          // So the caller can distinguish "said nothing" from "the browser
          // could not listen at all", which need different advice.
          recognitionError: recognitionErrorRef.current,
          recognitionRan: recognitionStartedRef.current,
        })
        resolveRef.current = null
      }
      recorder.start()
      recorderRef.current = recorder
      startRecognition()
      setRecording(true)
      setSeconds(0)

      tickRef.current = setInterval(() => {
        setSeconds((value) => {
          const next = value + 1
          // Hard stop so a forgotten recording cannot run forever.
          if (next >= MAX_SECONDS) recorder.state === 'recording' && recorder.stop()
          return next
        })
      }, 1000)
      return true
    } catch (err) {
      cleanup()
      setRecording(false)
      setError(
        err?.name === 'NotAllowedError'
          ? 'Microphone permission was denied. Allow access, or type your question instead.'
          : 'Could not start the microphone. Please type your question instead.',
      )
      return false
    }
  }, [supported, cleanup, startRecognition])

  const stop = useCallback(
    () =>
      new Promise((resolve) => {
        const recorder = recorderRef.current
        if (!recorder || recorder.state !== 'recording') {
          cleanup()
          setRecording(false)
          resolve(null)
          return
        }
        resolveRef.current = resolve
        recorder.stop()
      }),
    [cleanup],
  )

  const cancel = useCallback(() => {
    const recorder = recorderRef.current
    resolveRef.current = null
    if (recorder && recorder.state === 'recording') {
      recorder.onstop = null
      recorder.stop()
    }
    cleanup()
    setRecording(false)
    setSeconds(0)
  }, [cleanup])

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
