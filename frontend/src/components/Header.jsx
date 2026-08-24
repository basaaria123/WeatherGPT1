import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { LANGUAGES, profileLabel, t } from '../i18n/ui'
import { useStore } from '../store/useStore'

/** Compact app bar: identity, location, language, profile, connection state. */

const PROFILES = ['general', 'farmer', 'fisherman', 'traveler', 'commuter']

export default function Header({ onOpenLocation, onRefresh, refreshing }) {
  const language = useStore((s) => s.language)
  const setLanguage = useStore((s) => s.setLanguage)
  const userType = useStore((s) => s.userType)
  const setUserType = useStore((s) => s.setUserType)
  const location = useStore((s) => s.location)
  const socketState = useStore((s) => s.socketState)
  const dataSource = useStore((s) => s.dataSource)

  return (
    <header className="sticky top-0 z-30 border-b border-white/[0.07] bg-[rgb(5_13_26/0.72)] backdrop-blur-xl">
      <div className="mx-auto w-full max-w-7xl px-4 py-2.5 sm:px-6">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <Logo />
            <div className="min-w-0 leading-tight">
              <div className="text-[15px] font-semibold tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>
                Weather<span className="text-primary">GPT</span>
              </div>
              <div className="hidden truncate text-[10px] uppercase tracking-[0.16em] text-faint sm:block">
                {t(language, 'tagline')}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2">
            <ConnectionDot state={socketState} language={language} />
            {dataSource === 'fixture' && (
              <span
                title={t(language, 'simulatedNote')}
                className="rounded-[var(--radius-pill)] border border-caution/40 bg-caution/12
                           px-1.5 py-0.5 text-[9px] font-bold tracking-wider text-caution sm:px-2"
              >
                <span className="sm:hidden" aria-label={t(language, 'simulated')}>SIM</span>
                <span className="hidden sm:inline">{t(language, 'simulated')}</span>
              </span>
            )}

            <button
              type="button"
              onClick={onOpenLocation}
              className="flex max-w-[38vw] items-center gap-1.5 rounded-[var(--radius-pill)] border border-white/10
                         bg-white/[0.05] px-2.5 py-1.5 text-xs text-ink transition hover:border-white/25
                         hover:bg-white/[0.1] sm:max-w-none"
              title={t(language, 'changeLocation')}
            >
              <span aria-hidden="true" className="text-primary">◎</span>
              <span className="truncate font-medium">{location?.name ?? '—'}</span>
            </button>

            <Dropdown
              label={LANGUAGES.find((l) => l.code === language)?.label ?? 'EN'}
              ariaLabel={t(language, 'language')}
              items={LANGUAGES.map((l) => ({ value: l.code, label: l.label, hint: l.name }))}
              value={language}
              onSelect={setLanguage}
            />

            <Dropdown
              label={profileLabel(language, userType)}
              ariaLabel={t(language, 'profile')}
              items={PROFILES.map((p) => ({ value: p, label: profileLabel(language, p) }))}
              value={userType}
              onSelect={setUserType}
              className="hidden sm:block"
            />

            <button
              type="button"
              onClick={onRefresh}
              disabled={refreshing}
              aria-label={t(language, 'refresh')}
              title={t(language, 'refresh')}
              className="grid h-8 w-8 place-items-center rounded-full border border-white/10 bg-white/[0.05]
                         text-sm text-ink-soft transition hover:border-white/25 hover:bg-white/[0.1]
                         disabled:opacity-45"
            >
              <motion.span
                aria-hidden="true"
                animate={refreshing ? { rotate: 360 } : { rotate: 0 }}
                transition={refreshing ? { duration: 0.9, repeat: Infinity, ease: 'linear' } : { duration: 0.2 }}
              >
                ↻
              </motion.span>
            </button>
          </div>
        </div>

        {/* Profile selector moves below the bar on narrow screens rather than
            being hidden, so it stays reachable on a phone. */}
        <div className="mt-2 flex min-w-0 gap-1.5 pb-0.5 sm:hidden scroll-x">
          {PROFILES.map((profile) => (
            <button
              key={profile}
              type="button"
              onClick={() => setUserType(profile)}
              aria-pressed={userType === profile}
              className={`shrink-0 rounded-[var(--radius-pill)] border px-2.5 py-1 text-[11px] transition ${
                userType === profile
                  ? 'border-primary/60 bg-primary/15 text-primary'
                  : 'border-white/10 bg-white/[0.04] text-muted'
              }`}
            >
              {profileLabel(language, profile)}
            </button>
          ))}
        </div>
      </div>
    </header>
  )
}

function Logo() {
  return (
    <svg width="30" height="30" viewBox="0 0 64 64" fill="none" aria-hidden="true" className="shrink-0">
      <path
        d="M17 38a9 9 0 0 1 2.2-17.7 13 13 0 0 1 24.6 3.4A8.5 8.5 0 0 1 45 38Z"
        fill="#22d3ee"
        fillOpacity="0.2"
        stroke="#22d3ee"
        strokeWidth="2.4"
        strokeLinejoin="round"
      />
      <path d="M25 43l-2.5 7M33 43l-2.5 7M41 43l-2.5 7" stroke="#2dd4bf" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

function ConnectionDot({ state, language }) {
  const map = {
    open: { color: 'var(--color-safe)', label: t(language, 'connected') },
    connecting: { color: 'var(--color-caution)', label: t(language, 'reconnecting') },
    reconnecting: { color: 'var(--color-caution)', label: t(language, 'reconnecting') },
    closed: { color: 'var(--color-faint)', label: t(language, 'offlineAlerts') },
  }
  const tone = map[state] ?? map.closed
  return (
    <span title={tone.label} className="flex items-center gap-1.5 px-1" role="status" aria-label={tone.label}>
      <span
        className={`h-1.5 w-1.5 rounded-full ${state === 'open' ? '' : 'pulse-alert'}`}
        style={{ background: tone.color }}
      />
    </span>
  )
}

function Dropdown({ label, items, value, onSelect, ariaLabel, className = '' }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const onClick = (event) => {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false)
    }
    const onKey = (event) => event.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        type="button"
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-1 rounded-[var(--radius-pill)] border border-white/10 bg-white/[0.05]
                   px-2.5 py-1.5 text-xs font-medium text-ink transition hover:border-white/25 hover:bg-white/[0.1]"
      >
        {label}
        <span aria-hidden="true" className="text-[9px] text-faint">▾</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.ul
            role="listbox"
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.16 }}
            className="glass glass-raised absolute right-0 z-40 mt-1.5 min-w-[9.5rem] overflow-hidden p-1"
          >
            {items.map((item) => (
              <li key={item.value}>
                <button
                  type="button"
                  role="option"
                  aria-selected={item.value === value}
                  onClick={() => {
                    onSelect(item.value)
                    setOpen(false)
                  }}
                  className={`flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-1.5 text-left
                              text-xs transition hover:bg-white/[0.09] ${
                                item.value === value ? 'text-primary' : 'text-ink-soft'
                              }`}
                >
                  <span>{item.label}</span>
                  {item.hint && <span className="text-[9px] text-faint">{item.hint}</span>}
                </button>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  )
}
