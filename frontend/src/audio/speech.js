/**
 * Browser speech, shared by everything that talks.
 *
 * The server renders audio when it can reach a voice provider. When it cannot,
 * the browser's own synthesiser is the fallback — which is the difference
 * between "no audio today" and "no audio on this deployment", and worth having.
 *
 * The locale table covers every language the app ships. It used to cover six,
 * which meant a Tamil reader got an English voice reading Tamil text: the
 * wrong phonemes for the right words, which is worse than silence. A language
 * with no entry here is simply not spoken by the browser, and the server path
 * is the only one offered.
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

/** An utterance in the reader's language, or null when it cannot be spoken. */
export function utteranceFor(text, language) {
  if (!browserSpeechSupported() || !text?.trim()) return null
  const utterance = new window.SpeechSynthesisUtterance(text)
  utterance.lang = SPEECH_LOCALE[language] ?? SPEECH_LOCALE.en
  // Just under default. Synthesised speech at 1.0 runs slightly fast for
  // instructions someone is meant to act on, and this is the only pacing
  // control the platform actually gives us.
  utterance.rate = 0.95
  return utterance
}


/**
 * Puter's hosted voice, the browser's half of the fallback ladder.
 *
 * The full order is ElevenLabs → Puter → gTTS → the browser's own
 * synthesiser. The first and third of those live on the server and the second
 * does not — Puter is a browser SDK and cannot be called from Python — so the
 * server renders what it can and hands the client both the clip and the name
 * of whatever produced it. When that name is not "elevenlabs", the client
 * tries Puter first and only falls back to the server's clip if Puter cannot
 * speak. That keeps the requested order without a second round trip.
 *
 * Nothing here is required: the script tag loads async and may never arrive,
 * which is exactly why every call is feature-detected rather than assumed.
 */
const PUTER_TIMEOUT_MS = 9000

export const puterSpeechAvailable = () =>
  typeof window !== 'undefined' && typeof window.puter?.ai?.txt2speech === 'function'

/**
 * Returns a playable HTMLAudioElement, or null if Puter cannot speak this.
 *
 * Puter returns an <audio> element of its own; a slow or hung call is raced
 * against a timeout so a missing provider can never leave the button spinning.
 */
export async function puterSpeak(text, language) {
  if (!puterSpeechAvailable() || !text?.trim()) return null
  try {
    const spoken = await Promise.race([
      window.puter.ai.txt2speech(text, { language: SPEECH_LOCALE[language] ?? SPEECH_LOCALE.en }),
      new Promise((resolve) => setTimeout(() => resolve(null), PUTER_TIMEOUT_MS)),
    ])
    // Older builds hand back a URL rather than an element.
    if (!spoken) return null
    if (typeof spoken === 'string') return new Audio(spoken)
    return typeof spoken.play === 'function' ? spoken : null
  } catch {
    return null
  }
}
