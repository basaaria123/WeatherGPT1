import { localeTag } from './languages'

/**
 * Dates and relative times in the reader's language — or in digits.
 *
 * CLDR does this better than a hand-written table could, and the browser ships
 * it. The catch is that a runtime will happily accept a locale it has no data
 * for and answer in English: Chromium reports support for Punjabi and then
 * returns "Tue" and "this minute". Asking `supportedLocalesOf` is therefore not
 * enough — the only reliable test is to format and look at what comes back.
 *
 * When what comes back is Latin script for a language not written in Latin, the
 * fallback is digits: a date, a clock time. Both are things every reader of this
 * app already reads (temperatures, risk scores) and neither claims a language
 * the browser cannot actually render.
 */

const LATIN_SCRIPT_LANGUAGES = new Set(['en'])

function unlocalised(text, id) {
  return !LATIN_SCRIPT_LANGUAGES.has(id) && /[A-Za-z]/.test(text)
}

/** Short weekday name, or `d/M`. */
export function weekdayLabel(iso, id) {
  const at = new Date(iso)
  if (Number.isNaN(at.getTime())) return typeof iso === 'string' ? iso.slice(5) : '—'
  const digits = `${at.getDate()}/${at.getMonth() + 1}`
  const locale = localeTag(id)
  if (!locale) return digits
  try {
    const text = at.toLocaleDateString(locale, { weekday: 'short' })
    return unlocalised(text, id) ? digits : text
  } catch {
    return digits
  }
}

/** "5 minutes ago" in the reader's language, or the clock time it was taken. */
export function relativeLabel(iso, id) {
  if (!iso) return null
  const at = new Date(iso)
  if (Number.isNaN(at.getTime())) return null
  const clock = at.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const locale = localeTag(id)
  if (!locale) return clock
  const minutes = Math.max(0, Math.round((Date.now() - at.getTime()) / 60000))
  try {
    const fmt = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })
    const text = minutes < 60
      ? fmt.format(-minutes, 'minute')
      : fmt.format(-Math.round(minutes / 60), 'hour')
    return unlocalised(text, id) ? clock : text
  } catch {
    return clock
  }
}
