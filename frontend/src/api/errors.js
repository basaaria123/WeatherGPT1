import { ApiError } from './client'
import { t } from '../i18n/ui'

/**
 * The single place a failure becomes a sentence a person reads.
 *
 * Two things go wrong when a component renders `error.message`:
 *
 *   1. Only `ApiError` promises a safe message. A `TypeError` thrown by our own
 *      code inside the same `try` carries a developer's sentence — "Cannot read
 *      properties of undefined" — straight to the screen.
 *   2. Even a safe message is English, so a reader who set the interface to
 *      Tamil gets one English line in the middle of a Tamil page.
 *
 * `userMessage` closes both. It reads the stable `code` an `ApiError` carries
 * (see api/client.js) and returns the matching sentence from the interface
 * corpus; anything that is *not* an `ApiError` — any unexpected throw — comes
 * back as the generic sentence, because we cannot vouch for its text.
 *
 * The English original stays on `error.message` for the console and for logs.
 */

const KEY_FOR_CODE = {
  notFound: 'errNotFound',
  timeout: 'errTimeout',
  offline: 'errOffline',
  unavailable: 'errUnavailable',
  generic: 'errGeneric',
}

export function userMessage(error, language = 'en') {
  const key = error instanceof ApiError ? KEY_FOR_CODE[error.code] ?? 'errGeneric' : 'errGeneric'
  return t(language, key)
}
