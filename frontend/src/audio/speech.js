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
