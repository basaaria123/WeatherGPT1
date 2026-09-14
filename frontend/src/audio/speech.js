/**
 * Browser speech, shared by everything that talks.
 *
 * The server renders audio when it can reach a voice provider. When it cannot,
 * the browser's own synthesiser is the fallback — the difference between "no
 * audio today" and "no audio on this deployment", and worth having.
 *
 * THE BUG THIS FILE EXISTS TO NOT HAVE AGAIN
 *
 * Setting `utterance.lang = 'hi-IN'` does not get you a Hindi voice. It states
 * a preference. If the device has no Hindi voice installed, the platform falls
 * back to its default — an English one — and hands it Devanagari text. An
 * English voice given Devanagari says nothing for the letters it cannot map and
 * reads straight through the Latin digits, so an emergency message came out as
 * "eighty. sixty three." and nothing else.
 *
 * That is the "it only reads the numbers" report, and it is not a text problem:
 * the script handed to TTS was always the complete message. It is a *voice
 * selection* problem, and the fix is to pick a real voice and to refuse rather
 * than mis-read when there is not one.
 */

export const SPEECH_LOCALE = {
  en: 'en-IN',
  hi: 'hi-IN',
  te: 'te-IN',
  bn: 'bn-IN',
  mr: 'mr-IN',
  as: 'as-IN',
  ta: 'ta-IN',
  kn: 'kn-IN',
  ml: 'ml-IN',
  gu: 'gu-IN',
  pa: 'pa-IN',
}

export const browserSpeechSupported = () =>
  typeof window !== 'undefined' &&
  'speechSynthesis' in window &&
  'SpeechSynthesisUtterance' in window

/**
 * The device's voices, which are not there on the first call.
 *
 * Chrome populates the list asynchronously and returns `[]` until it has —
 * so the very first Listen of a session picked no voice at all, every time,
 * and the second one worked. `voiceschanged` is the event that says the list
 * has arrived; this resolves on it, or on a short timeout for the browsers
 * that populate synchronously and never fire it.
 */
let voicesPromise = null

export function loadVoices() {
  if (!browserSpeechSupported()) return Promise.resolve([])
  const existing = window.speechSynthesis.getVoices()
  if (existing.length) return Promise.resolve(existing)
  if (voicesPromise) return voicesPromise

  voicesPromise = new Promise((resolve) => {
    let settled = false
    const done = () => {
      if (settled) return
      settled = true
      window.speechSynthesis.removeEventListener?.('voiceschanged', done)
      resolve(window.speechSynthesis.getVoices())
    }
    window.speechSynthesis.addEventListener?.('voiceschanged', done)
    // Safari fires nothing and is ready immediately; do not wait forever for an
    // event that is not coming.
    setTimeout(done, 1200)
  })
  return voicesPromise
}

/**
 * A voice that can actually pronounce this language, or null.
 *
 * Three passes, narrowing: the exact locale (`hi-IN`), then any voice for the
 * language (`hi-*`, which is how a device with `hi_IN` or plain `hi` is
 * caught), and nothing else. Deliberately no "close enough" pass: `en-US` is
 * not a substitute for `ta-IN`, and pretending otherwise is what produced the
 * number-reading.
 */
export function voiceFor(voices, language) {
  const locale = (SPEECH_LOCALE[language] ?? SPEECH_LOCALE.en).toLowerCase()
  const base = locale.split('-')[0]
  const tag = (voice) => (voice.lang || '').replace('_', '-').toLowerCase()

  return (
    voices.find((voice) => tag(voice) === locale) ??
    voices.find((voice) => tag(voice).split('-')[0] === base) ??
    null
  )
}

/** Can this device speak this language at all? */
export async function canSpeakLanguage(language) {
  if (!browserSpeechSupported()) return false
  return Boolean(voiceFor(await loadVoices(), language))
}

/**
 * An utterance in the reader's language, or null when it cannot be spoken.
 *
 * Async now, because the voice list is. Callers awaiting a null must fall back
 * to showing the text rather than speaking it — which is the correct outcome:
 * an emergency instruction read in the wrong phonemes, or read as its digits
 * alone, is worse than one that is only on the screen.
 */
export async function utteranceFor(text, language) {
  if (!browserSpeechSupported() || !text?.trim()) return null

  const voice = voiceFor(await loadVoices(), language)
  if (!voice) return null

  const utterance = new window.SpeechSynthesisUtterance(text)
  utterance.voice = voice
  // Both: the voice is what does the pronouncing, the tag is what some engines
  // use to pick a dictionary within a voice.
  utterance.lang = voice.lang || SPEECH_LOCALE[language] || SPEECH_LOCALE.en
  // Just under default. Synthesised speech at 1.0 runs slightly fast for
  // instructions someone is meant to act on, and this is the only pacing
  // control the platform actually gives us.
  utterance.rate = 0.95
  return utterance
}
