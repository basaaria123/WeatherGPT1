import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../../api/client'
import { userMessage } from '../../api/errors'
import {
  isValidPhone,
  maskPhone,
  phoneSession,
  requestCode,
  verifyCode,
} from '../../auth/session'
import { LANGUAGE_CATALOG, withServerLanguages } from '../../i18n/languages'
import { safeNative } from '../../i18n/scriptSupport'
import { ROLES } from '../../i18n/roles'
import { profileLabel, t } from '../../i18n/ui'
import { useStore } from '../../store/useStore'

/**
 * The four onboarding panels.
 *
 * They share a shape — a heading, one line of why it is being asked, and the
 * answer — because the reader should be able to see at a glance that this is
 * short. None of them can be got wrong: every panel has a way forward that
 * needs no input.
 */

const RESEND_SECONDS = 30

function Heading({ title, lead }) {
  return (
    <>
      <h1
        className="text-[1.9rem] font-semibold leading-tight tracking-tight sm:text-[2.4rem]"
        style={{ fontFamily: 'var(--font-display)' }}
      >
        {title}
      </h1>
      <p className="mt-2.5 max-w-lg text-[13.5px] leading-relaxed text-muted">{lead}</p>
    </>
  )
}

function PrimaryButton({ children, ...props }) {
  return (
    <button
      type="button"
      className="rounded-[var(--radius-pill)] bg-primary px-5 py-2.5 text-[13px] font-semibold text-[rgb(var(--wx-scrim))]
                 transition hover:opacity-90 active:scale-[0.99] disabled:opacity-45"
      {...props}
    >
      {children}
    </button>
  )
}

// --- 1. Where are you? ------------------------------------------------------

const SUGGESTIONS = ['Vijayawada', 'Guwahati', 'Mumbai', 'Chennai', 'Kolkata', 'New Delhi']

export function LocationStep({ onNext }) {
  const language = useStore((s) => s.language)
  const location = useStore((s) => s.location)
  const setLocation = useStore((s) => s.setLocation)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('idle') // idle | loading | locating | error
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  useEffect(() => {
    const timer = window.setTimeout(() => inputRef.current?.focus(), 140)
    return () => window.clearTimeout(timer)
  }, [])

  const resolve = async (name) => {
    const value = (name ?? query).trim()
    if (!value) return
    setStatus('loading')
    setError(null)
    try {
      const result = await api.geocode(value)
      setLocation(result.location)
      setStatus('idle')
      onNext()
    } catch (err) {
      setStatus('error')
      setError(userMessage(err, language))
    }
  }

  /**
   * The device position, resolved to the nearest place the app actually covers.
   *
   * Described as the nearest covered city rather than "your location", because
   * that is what it is: the backend has a fixed gazetteer, not a reverse
   * geocoder for every village in India.
   */
  const locate = () => {
    if (!navigator.geolocation) return
    setStatus('locating')
    setError(null)
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const result = await api.reverseGeocode(coords.latitude, coords.longitude)
          setLocation(result.location)
          setStatus('idle')
          onNext()
        } catch (err) {
          setStatus('error')
          setError(userMessage(err, language))
        }
      },
      () => {
        setStatus('error')
        setError(t(language, 'locationDenied'))
      },
      { timeout: 8000 },
    )
  }

  return (
    <div>
      <Heading title={t(language, 'onbLocationTitle')} lead={t(language, 'onbLocationLead')} />

      <div className="mt-6 flex flex-col gap-2.5 sm:flex-row">
        <input
          ref={inputRef}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => event.key === 'Enter' && resolve()}
          placeholder={t(language, 'searchLocation')}
          aria-label={t(language, 'searchLocation')}
          className="min-w-0 flex-1 rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.12)]
                     bg-[rgb(var(--wx-tint)/0.05)] px-4 py-2.5 text-[14px] text-ink outline-none
                     transition placeholder:text-faint focus:border-primary/50"
        />
        <PrimaryButton onClick={() => resolve()} disabled={!query.trim() || status === 'loading'}>
          {status === 'loading' ? '…' : t(language, 'onbNext')}
        </PrimaryButton>
      </div>

      {navigator.geolocation && (
        <button
          type="button"
          onClick={locate}
          disabled={status === 'locating'}
          className="mt-3 inline-flex min-h-[36px] items-center text-[12.5px] text-primary transition
                     hover:opacity-80 disabled:opacity-50"
        >
          ◎ {status === 'locating' ? `${t(language, 'onbUseLocation')}…` : t(language, 'onbUseLocation')}
        </button>
      )}

      <div className="mt-5 flex flex-wrap gap-1.5">
        {SUGGESTIONS.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => resolve(name)}
            className="min-h-[36px] rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.10)]
                       bg-[rgb(var(--wx-tint)/0.04)] px-3.5 text-[12.5px] text-muted transition
                       hover:border-primary/40 hover:text-ink"
          >
            {name}
          </button>
        ))}
      </div>

      {error && <p className="mt-4 text-[12.5px] text-danger">{error}</p>}

      {location?.name && !error && (
        <p className="mt-5 text-[12px] text-faint">
          ◎ {location.name}
          {location.admin1 && location.admin1 !== location.name ? `, ${location.admin1}` : ''}
        </p>
      )}
    </div>
  )
}

// --- 2. How should WeatherGPT help you? -------------------------------------

// Shared with the header selector, so the nine roles offered here are exactly
// the nine the rest of the app can switch between. A role on this screen that
// the advisory engine cannot tell apart would be a promise the product breaks
// on the very next screen.

export function RoleStep({ onNext }) {
  const language = useStore((s) => s.language)
  const userType = useStore((s) => s.userType)
  const setUserType = useStore((s) => s.setUserType)

  return (
    <div>
      <Heading title={t(language, 'onbRoleTitle')} lead={t(language, 'onbRoleLead')} />

      {/* Two columns even at 320px: nine single-file rows would push the last
          roles below the fold, and a role nobody scrolls to is a role nobody
          picks. Three columns once there is room for them. */}
      <div className="mt-6 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {ROLES.map((role) => {
          const active = role.id === userType
          return (
            <button
              key={role.id}
              type="button"
              onClick={() => { setUserType(role.id); onNext() }}
              aria-pressed={active}
              className={`flex min-h-[56px] min-w-0 items-center gap-2.5 rounded-[var(--radius-card)] border px-3 py-2.5
                          text-left transition ${
                            active
                              ? 'border-primary/60 bg-primary/10'
                              : 'border-[rgb(var(--wx-tint)/0.10)] bg-[rgb(var(--wx-tint)/0.03)] hover:border-[rgb(var(--wx-tint)/0.28)]'
                          }`}
            >
              <span aria-hidden="true" className="shrink-0 text-xl">{role.icon}</span>
              <span
                className={`min-w-0 text-[13px] font-medium leading-tight ${
                  active ? 'text-primary' : 'text-ink'
                }`}
              >
                {profileLabel(language, role.id)}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

// --- 3. How should WeatherGPT speak to you? ---------------------------------

export function LanguageStep({ onNext }) {
  const language = useStore((s) => s.language)
  const setLanguage = useStore((s) => s.setLanguage)
  const capabilities = useStore((s) => s.capabilities)

  /*
   * Only the languages the backend can actually answer in.
   *
   * The selector in the header offers thirty-five, and is honest about which
   * of them are answered in English. Onboarding is the wrong moment for that
   * distinction — a reader choosing here should get what they picked — so this
   * step shows the fully supported set and leaves the rest to the header.
   */
  const options = useMemo(
    () => withServerLanguages(LANGUAGE_CATALOG, capabilities?.languages).filter((entry) => entry.translation),
    [capabilities?.languages],
  )

  return (
    <div>
      <Heading title={t(language, 'onbLanguageTitle')} lead={t(language, 'onbLanguageLead')} />

      <div className="mt-6 grid gap-2 sm:grid-cols-3">
        {options.map((entry) => {
          const active = entry.id === language
          const native = safeNative(entry)
          return (
            <button
              key={entry.id}
              type="button"
              onClick={() => { setLanguage(entry.id); onNext() }}
              aria-pressed={active}
              lang={entry.id}
              className={`flex min-h-[56px] flex-col justify-center rounded-[var(--radius-card)] border px-4 py-3
                          text-left transition ${
                            active
                              ? 'border-primary/60 bg-primary/10'
                              : 'border-[rgb(var(--wx-tint)/0.10)] bg-[rgb(var(--wx-tint)/0.03)] hover:border-[rgb(var(--wx-tint)/0.28)]'
                          }`}
            >
              <span className={`text-[15px] font-medium ${active ? 'text-primary' : 'text-ink'}`}>
                {native || entry.english}
              </span>
              {native && <span className="text-[11px] text-faint">{entry.english}</span>}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// --- 4. Save this, or don't --------------------------------------------------

export function IdentityStep({ onDone }) {
  const language = useStore((s) => s.language)
  const setSession = useStore((s) => s.setSession)

  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [expected, setExpected] = useState(null)
  const [stage, setStage] = useState('phone') // phone | sending | code | verifying | done
  const [error, setError] = useState(null)
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return undefined
    const timer = window.setTimeout(() => setCooldown((n) => n - 1), 1000)
    return () => window.clearTimeout(timer)
  }, [cooldown])

  const send = async () => {
    setError(null)
    if (!isValidPhone(phone)) { setError('invalidPhone'); return }
    setStage('sending')
    const result = await requestCode(phone)
    if (!result.ok) { setStage('phone'); setError(result.error); return }
    setExpected(result.code)
    setCooldown(RESEND_SECONDS)
    setStage('code')
  }

  const submit = async () => {
    setError(null)
    setStage('verifying')
    const result = await verifyCode(expected, code)
    if (!result.ok) { setStage('code'); setError(result.error); return }
    setSession(phoneSession(phone))
    setStage('done')
    window.setTimeout(onDone, 900)
  }

  return (
    <div>
      <Heading title={t(language, 'onbIdentityTitle')} lead={t(language, 'onbIdentityLead')} />

      {stage === 'done' ? (
        <div className="mt-7 flex items-center gap-2.5 text-[15px] font-medium text-safe">
          <span aria-hidden="true">✓</span>
          <span>{t(language, 'verified')} · {maskPhone(phone)}</span>
        </div>
      ) : (
        <div className="mt-6">
          {stage === 'phone' || stage === 'sending' ? (
            <div className="flex flex-col gap-2.5 sm:flex-row">
              <div className="flex min-w-0 flex-1 items-center gap-2 rounded-[var(--radius-pill)] border
                              border-[rgb(var(--wx-tint)/0.12)] bg-[rgb(var(--wx-tint)/0.05)] px-4 py-2.5
                              focus-within:border-primary/50">
                <span className="shrink-0 text-[14px] text-muted">+91</span>
                <input
                  value={phone}
                  onChange={(event) => setPhone(event.target.value.replace(/\D/g, '').slice(0, 10))}
                  onKeyDown={(event) => event.key === 'Enter' && send()}
                  inputMode="numeric"
                  autoComplete="tel-national"
                  aria-label="Phone number"
                  placeholder="98765 43210"
                  className="min-w-0 flex-1 bg-transparent text-[14px] tabular-nums text-ink outline-none placeholder:text-faint"
                />
              </div>
              <PrimaryButton onClick={send} disabled={stage === 'sending'}>
                {stage === 'sending' ? t(language, 'sendingOtp') : t(language, 'sendOtp')}
              </PrimaryButton>
            </div>
          ) : (
            <div>
              <label htmlFor="wx-otp" className="text-[12px] text-muted">{t(language, 'enterOtp')}</label>
              <div className="mt-2 flex flex-col gap-2.5 sm:flex-row">
                <input
                  id="wx-otp"
                  value={code}
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                  onKeyDown={(event) => event.key === 'Enter' && submit()}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="——————"
                  className="min-w-0 flex-1 rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.12)]
                             bg-[rgb(var(--wx-tint)/0.05)] px-4 py-2.5 text-[16px] tracking-[0.4em] tabular-nums
                             text-ink outline-none transition placeholder:text-faint focus:border-primary/50"
                />
                <PrimaryButton onClick={submit} disabled={stage === 'verifying'}>
                  {stage === 'verifying' ? t(language, 'verifying') : t(language, 'verify')}
                </PrimaryButton>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
                <button
                  type="button"
                  onClick={send}
                  disabled={cooldown > 0}
                  className="inline-flex min-h-[36px] items-center text-[12.5px] text-primary transition
                             hover:opacity-80 disabled:text-faint"
                >
                  {cooldown > 0
                    ? `${t(language, 'resendIn')} ${cooldown}s`
                    : t(language, 'resendOtp')}
                </button>
                <span className="text-[12px] text-faint">{maskPhone(phone)}</span>
              </div>

              {/* The prototype's own disclosure. There is no SMS provider here,
                  so the code is shown rather than claimed to have been sent. */}
              <div className="mt-4 rounded-[var(--radius-card)] border border-caution/30 bg-caution/8 px-3.5 py-2.5">
                <p className="text-[11.5px] leading-relaxed text-caution">{t(language, 'demoNotice')}</p>
                <p className="mt-1 text-[13px] font-semibold tabular-nums tracking-[0.2em] text-ink">
                  {t(language, 'demoCode')}: {expected}
                </p>
              </div>
            </div>
          )}

          {error && <p className="mt-3 text-[12.5px] text-danger">{t(language, error)}</p>}
        </div>
      )}

      {stage !== 'done' && (
        <button
          type="button"
          onClick={onDone}
          className="mt-7 inline-flex min-h-[40px] items-center text-[13px] text-muted underline
                     decoration-[rgb(var(--wx-tint)/0.25)] underline-offset-4 transition hover:text-ink"
        >
          {t(language, 'onbContinueGuest')} →
        </button>
      )}
    </div>
  )
}
