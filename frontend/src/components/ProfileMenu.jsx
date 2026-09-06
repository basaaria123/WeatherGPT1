import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { maskPhone } from '../auth/session'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'

/**
 * Who you are, and what that changes.
 *
 * Guest is a complete way to use WeatherGPT, not a trial — every panel on the
 * dashboard works without a phone number. The one thing it cannot do is send
 * an SMS to a number nobody has given, so that is the one thing this menu asks
 * about, once, where it is relevant.
 *
 * It also states plainly that no SMS provider is connected in this prototype.
 * A toggle that silently does nothing is worse than no toggle.
 */

export default function ProfileMenu({ onSignIn }) {
  const language = useStore((s) => s.language)
  const session = useStore((s) => s.session)
  const signOut = useStore((s) => s.signOut)
  const smsOptIn = useStore((s) => s.smsOptIn)
  const setSmsOptIn = useStore((s) => s.setSmsOptIn)
  const reduced = useReducedMotion()

  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const onPointer = (event) => {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false)
    }
    const onKey = (event) => event.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const signedIn = session?.mode === 'phone'

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={t(language, 'profile')}
        data-profile-trigger
        className={`grid h-8 w-8 place-items-center rounded-full border text-[13px] transition ${
          signedIn
            ? 'border-primary/50 bg-primary/12 text-primary'
            : 'border-[rgb(var(--wx-tint)/0.12)] bg-[rgb(var(--wx-tint)/0.05)] text-ink-soft hover:border-[rgb(var(--wx-tint)/0.28)]'
        }`}
      >
        <span aria-hidden="true">{signedIn ? '✓' : '👤'}</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            data-profile-menu
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: reduced ? 0.01 : 0.16 }}
            className="glass glass-raised fixed right-3 top-14 z-50 w-[min(19rem,calc(100vw-1.5rem))] overflow-hidden
                       bg-[rgb(var(--wx-scrim)/0.985)] p-0 backdrop-blur-2xl sm:absolute sm:right-0 sm:top-full sm:mt-1.5"
          >
            <div className="border-b border-[rgb(var(--wx-tint)/0.08)] px-3.5 py-3">
              <div className="text-[10px] uppercase tracking-[0.14em] text-faint">
                {t(language, 'myWeatherGPT')}
              </div>
              <div className="mt-1 text-[14px] font-semibold text-ink">
                {signedIn ? maskPhone(session.phone) : t(language, 'guest')}
              </div>
              {!signedIn && (
                <p className="mt-1 text-[11.5px] leading-relaxed text-muted">{t(language, 'guestNote')}</p>
              )}
            </div>

            {/* SMS: the one capability a session actually changes. */}
            <div className="border-b border-[rgb(var(--wx-tint)/0.08)] px-3.5 py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-[12.5px] font-medium text-ink">{t(language, 'smsAlerts')}</span>
                {signedIn ? (
                  <button
                    type="button"
                    role="switch"
                    aria-checked={smsOptIn}
                    onClick={() => setSmsOptIn(!smsOptIn)}
                    className={`relative h-[22px] w-10 shrink-0 rounded-full border transition ${
                      smsOptIn
                        ? 'border-primary/60 bg-primary/25'
                        : 'border-[rgb(var(--wx-tint)/0.15)] bg-[rgb(var(--wx-tint)/0.06)]'
                    }`}
                  >
                    <span
                      aria-hidden="true"
                      className="absolute top-[2px] h-[16px] w-[16px] rounded-full transition-all"
                      style={{
                        left: smsOptIn ? '20px' : '2px',
                        background: smsOptIn ? 'var(--color-primary)' : 'rgb(var(--wx-tint) / 0.4)',
                      }}
                    />
                  </button>
                ) : (
                  <span className="shrink-0 text-[11px] text-faint">{t(language, 'smsOff')}</span>
                )}
              </div>

              {signedIn ? (
                <>
                  <p className="mt-1 text-[11px] text-muted">
                    {smsOptIn ? t(language, 'smsHighOnly') : t(language, 'smsOff')}
                  </p>
                  {/* Never claim a message was sent when nothing can send one. */}
                  <p className="mt-1.5 text-[10.5px] leading-relaxed text-caution">
                    {t(language, 'smsMockNote')}
                  </p>
                </>
              ) : (
                <>
                  <p className="mt-1 text-[11px] leading-relaxed text-muted">
                    {t(language, 'smsGuestBlocked')}
                  </p>
                  <button
                    type="button"
                    onClick={() => { setOpen(false); onSignIn() }}
                    className="mt-2 text-[12px] font-medium text-primary transition hover:opacity-80"
                  >
                    {t(language, 'smsEnableCta')}
                  </button>
                </>
              )}
            </div>

            <div className="px-2 py-2">
              {signedIn ? (
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => { setOpen(false); signOut() }}
                  className="w-full rounded-lg px-2 py-2 text-left text-[12.5px] text-ink-soft transition
                             hover:bg-[rgb(var(--wx-tint)/0.08)]"
                >
                  {t(language, 'signOut')}
                </button>
              ) : (
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => { setOpen(false); onSignIn() }}
                  className="w-full rounded-lg px-2 py-2 text-left text-[12.5px] text-primary transition
                             hover:bg-[rgb(var(--wx-tint)/0.08)]"
                >
                  {t(language, 'signIn')} →
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
