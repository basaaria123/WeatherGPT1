import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { LANGUAGES, profileLabel, t } from '../i18n/ui'
import { LOGO_SRC } from './SplashScreen'
import { useStore } from '../store/useStore'

/** Compact app bar: identity, location, language, profile, connection state. */

const PROFILES = ['general', 'farmer', 'fisherman', 'traveler', 'commuter']

export default function Header({ onHome, onOpenLocation, onRefresh, refreshing }) {
  const language = useStore((s) => s.language)
  const setLanguage = useStore((s) => s.setLanguage)
  const userType = useStore((s) => s.userType)
  const setUserType = useStore((s) => s.setUserType)
  const location = useStore((s) => s.location)
  const socketState = useStore((s) => s.socketState)
  const dataSource = useStore((s) => s.dataSource)

  return (
    <header className="sticky top-0 z-30 border-b border-[rgb(var(--wx-tint)/0.07)] bg-[rgb(var(--wx-scrim)/0.72)] backdrop-blur-xl">
      <div className="mx-auto w-full max-w-7xl px-4 py-2.5 sm:px-6">
        <div className="flex items-center justify-between gap-3">
          {/* The whole brand block is the home control, not just the mark.
              It returns to the landing page directly — the splash belongs to
              first load and is never replayed from here. */}
          <button
            type="button"
            onClick={onHome}
            aria-label={t(language, 'goHome')}
            title={t(language, 'goHome')}
            className="group flex min-w-0 flex-1 cursor-pointer items-center gap-2.5 rounded-xl px-1 py-0.5
                       text-left transition hover:opacity-90 active:scale-[0.99]"
          >
            <Logo />
            <div className="hidden min-w-0 leading-tight min-[380px]:block">
              <div
                className="truncate text-[15px] font-semibold tracking-tight transition-colors
                           group-hover:text-primary"
                style={{ fontFamily: 'var(--font-display)' }}
              >
                Weather<span className="text-primary">GPT</span>
              </div>
              <div className="hidden truncate text-[11px] uppercase tracking-[0.16em] text-faint sm:block">
                {t(language, 'tagline')}
              </div>
            </div>
          </button>

          <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
            <ConnectionDot state={socketState} language={language} />
            {dataSource === 'fixture' && (
              <span
                title={t(language, 'simulatedNote')}
                className="rounded-[var(--radius-pill)] border border-caution/40 bg-caution/12
                           px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-caution sm:px-2"
              >
                <span className="sm:hidden" aria-label={t(language, 'simulated')}>SIM</span>
                <span className="hidden sm:inline">{t(language, 'simulated')}</span>
              </span>
            )}

            <button
              type="button"
              onClick={onOpenLocation}
              className="flex max-w-[30vw] items-center gap-1.5 sm:max-w-none rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.10)]
                         bg-[rgb(var(--wx-tint)/0.05)] px-2.5 py-1.5 text-xs text-ink transition hover:border-[rgb(var(--wx-tint)/0.25)]
                         hover:bg-[rgb(var(--wx-tint)/0.1)] sm:max-w-none"
              title={t(language, 'changeLocation')}
            >
              <span aria-hidden="true" className="text-primary">◎</span>
              <span className="truncate font-medium">{location?.name ?? '—'}</span>
            </button>

            <Dropdown
              label={LANGUAGES.find((l) => l.code === language)?.label ?? 'English'}
              shortLabel={LANGUAGES.find((l) => l.code === language)?.short ?? 'EN'}
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
              className="grid h-8 w-8 place-items-center rounded-full border border-[rgb(var(--wx-tint)/0.10)] bg-[rgb(var(--wx-tint)/0.05)]
                         text-sm text-ink-soft transition hover:border-[rgb(var(--wx-tint)/0.25)] hover:bg-[rgb(var(--wx-tint)/0.1)]
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
                  : 'border-[rgb(var(--wx-tint)/0.10)] bg-[rgb(var(--wx-tint)/0.04)] text-muted'
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

/**
 * Brand mark.
 *
 * Uses the official artwork when present, scaled and clipped to its emblem so
 * the wordmark beside it is not duplicated. Falls back to the built-in mark if
 * the file is missing, so the header never shows a broken image.
 */
function Logo() {
  const [failed, setFailed] = useState(false)

  if (!failed) {
    return (
      // The emblem sits at x 0.204–0.860, y 0.072–0.620 of the square artwork,
      // above the wordmark. Rendering the file at 46px and offsetting by those
      // measurements puts the whole badge — and nothing else — in the 30px box,
      // so the header shows the official mark rather than a slice of it.
      <span className="relative h-[30px] w-[30px] shrink-0 overflow-hidden rounded-lg">
        <img
          src={LOGO_SRC}
          alt=""
          aria-hidden="true"
          onError={() => setFailed(true)}
          className="absolute max-w-none"
          style={{ width: '46px', height: '46px', left: '-9.5px', top: '-1px' }}
          draggable="false"
        />
      </span>
    )
  }

  return <FallbackMark />
}

function FallbackMark() {
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
    polling: { color: 'var(--color-accent)', label: t(language, 'pollingAlerts') },
    connecting: { color: 'var(--color-caution)', label: t(language, 'reconnecting') },
    reconnecting: { color: 'var(--color-caution)', label: t(language, 'reconnecting') },
    closed: { color: 'var(--color-faint)', label: t(language, 'offlineAlerts') },
  }
  const tone = map[state] ?? map.closed
  return (
    <span title={tone.label} className="flex items-center gap-1.5 px-1" role="status" aria-label={tone.label}>
      <span
        className={`h-1.5 w-1.5 rounded-full ${state === 'open' || state === 'polling' ? '' : 'pulse-alert'}`}
        style={{ background: tone.color }}
      />
    </span>
  )
}

function Dropdown({ label, shortLabel, items, value, onSelect, ariaLabel, className = '' }) {
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
        className="flex items-center gap-1 rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.10)] bg-[rgb(var(--wx-tint)/0.05)]
                   px-2.5 py-1.5 text-xs font-medium text-ink transition hover:border-[rgb(var(--wx-tint)/0.25)] hover:bg-[rgb(var(--wx-tint)/0.1)]"
      >
        {shortLabel ? (
          <>
            <span className="sm:hidden">{shortLabel}</span>
            <span className="hidden sm:inline">{label}</span>
          </>
        ) : (
          label
        )}
        <span aria-hidden="true" className="text-[10px] text-faint">▾</span>
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
                              text-xs transition hover:bg-[rgb(var(--wx-tint)/0.09)] ${
                                item.value === value ? 'text-primary' : 'text-ink-soft'
                              }`}
                >
                  <span>{item.label}</span>
                  {item.hint && <span className="text-[10px] text-faint">{item.hint}</span>}
                </button>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  )
}
