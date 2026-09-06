/**
 * Who the reader is, for the prototype.
 *
 * THIS IS NOT AUTHENTICATION. No credential leaves the browser, no message is
 * sent, and nothing here is checked by a server. It exists so the product's
 * shape — guest by default, phone optional, SMS gated behind a verified number
 * — can be demonstrated and reviewed before a real identity service is wired
 * in behind it.
 *
 * The seam is deliberate: `requestCode` and `verifyCode` are the only two
 * functions that would change. Replace their bodies with calls to a real OTP
 * endpoint and the rest of the app is unaffected, because nothing outside this
 * module knows how a session is established.
 *
 * Two rules the mock keeps, so it cannot be mistaken for the real thing:
 *
 *   1. It never claims a message was sent. The code is returned to the caller
 *      and shown on screen, labelled as a demo code.
 *   2. It never grants anything a real session would not. A guest can use the
 *      whole product; only SMS delivery — the one thing that genuinely needs a
 *      verified number — is withheld.
 */

const STORAGE_KEY = 'weathergpt:session'

/** Indian mobile numbers: ten digits, first one 6–9. */
const PHONE = /^[6-9]\d{9}$/

export const GUEST = { mode: 'guest', phone: null, verifiedAt: null }

export function isValidPhone(value) {
  return PHONE.test(String(value ?? '').replace(/\D/g, ''))
}

export function normalisePhone(value) {
  return String(value ?? '').replace(/\D/g, '').slice(-10)
}

export function loadSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return GUEST
    const parsed = JSON.parse(raw)
    return parsed?.mode === 'phone' && parsed.phone ? parsed : GUEST
  } catch {
    return GUEST
  }
}

export function saveSession(session) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  } catch {
    /* private mode or blocked storage — the session is a convenience */
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* nothing to do */
  }
}

/**
 * "Send" a one-time code.
 *
 * The code is generated here and handed straight back, because there is no
 * channel to send it down. A real implementation posts the number to an OTP
 * service and returns nothing but a request id — at which point the `code`
 * field disappears from this contract and the UI stops displaying it.
 */
export async function requestCode(phone) {
  const number = normalisePhone(phone)
  if (!isValidPhone(number)) {
    return { ok: false, error: 'invalidPhone' }
  }
  // A real request has latency; showing none makes the UI look untested.
  await new Promise((resolve) => setTimeout(resolve, 550))
  const code = String(Math.floor(100000 + Math.random() * 900000))
  return { ok: true, phone: number, code, delivered: false }
}

/** Check a code against the one this browser generated. Nothing more. */
export async function verifyCode(expected, entered) {
  await new Promise((resolve) => setTimeout(resolve, 450))
  const value = String(entered ?? '').replace(/\D/g, '')
  if (value.length !== 6) return { ok: false, error: 'incompleteCode' }
  if (value !== expected) return { ok: false, error: 'wrongCode' }
  return { ok: true }
}

export function phoneSession(phone) {
  return { mode: 'phone', phone: normalisePhone(phone), verifiedAt: new Date().toISOString() }
}

/** Masked for display: the reader confirms it, nobody else reads it over a shoulder. */
export function maskPhone(phone) {
  const number = normalisePhone(phone)
  return number.length === 10 ? `+91 ${number.slice(0, 2)}••• ${number.slice(-3)}` : ''
}
