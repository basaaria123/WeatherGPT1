import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { ROLE_ICONS, ROLE_IDS } from '../i18n/roles'
import { profileLabel, t } from '../i18n/ui'
import LanguagePicker from './LanguagePicker'
import ProfileMenu from './ProfileMenu'
import { LOGO_SRC } from './SplashScreen'
import { useStore } from '../store/useStore'
import Icon from './ui/Icon'

/**
 * The app bar, as the reference draws it.
 *
 * Three rows, and which of them appear depends on the destination:
 *
 *   1  the mark, the name, and the icon cluster            always
 *   2  location · role · language, as three pills          Home / Forecast
 *   3  a search field                                      Home / Map
 *
 * The reference varies row 1 per screen — a back arrow and a subtitle on the
 * assistant, a map glyph and a layer control on the map, a calendar and an
 * overflow on the forecast — so `screen` is a prop rather than the header being
 * five near-copies.
 *
 * The icon cluster carries everything the brief lists: connection state, the
 * alert bell with its count, the identity menu, the appearance toggle and a
 * manual refresh. They are all one drawing style at one weight, which is the
 * single biggest difference from what was here before — a row of emoji and
 * typographic glyphs reads as five different hands.
 */

const PROFILES = ROLE_IDS

// Which of the three rows each destination shows, and what marks row 1.
const SCREENS = {
  home: { glyph: 'cloud', pills: true, search: true },
  ai: { glyph: 'cloud', pills: true, subtitle: 'assistantSubtitle', back: true },
  // No trailing control: the layer switcher is on the map itself, two
  // rows down, and a sixth icon here truncates the wordmark at 390px.
  map: { glyph: 'layers', pills: false, search: true },
  alerts: { glyph: 'cloud', pills: false },
  // No trailing control: at 390px a sixth icon pushed the wordmark into
  // an ellipsis, and everything it could have opened is reachable already.
  forecast: { glyph: 'calendar', pills: true },
}

export default function Header({
  screen = 'home',
  onHome,
  onBack,
  onOpenLocation,
  onRefresh,
  refreshing,
  onSignIn,
  onSearch,
  onTrailing,
}) {
  const language = useStore((s) => s.language)
  const userType = useStore((s) => s.userType)
  const setUserType = useStore((s) => s.setUserType)
  const location = useStore((s) => s.location)
  const socketState = useStore((s) => s.socketState)
  const dataSource = useStore((s) => s.dataSource)
  const appearance = useStore((s) => s.appearance)
  const setAppearance = useStore((s) => s.setAppearance)
  const alertCount = useStore((s) => s.alerts.length)

  const spec = SCREENS[screen] ?? SCREENS.home

  return (
    <header className="wx-chrome wx-chrome-top sticky top-0 z-30">
      <div className="wx-shell px-3.5 pb-2.5 pt-3">
        {/* --- Row 1: mark, name, controls -------------------------------- */}
        <div className="flex items-center gap-2">
          {/* On a sub-page the way back rides in the header, where it stays
              reachable however far down the page the reader has scrolled. */}
          {spec.back && onBack && (
            <button
              type="button"
              onClick={onBack}
              aria-label={t(language, 'mapBack')}
              title={t(language, 'mapBack')}
              className="-ml-1 grid h-7 w-7 shrink-0 place-items-center rounded-full text-ink-soft
                         transition hover:bg-[rgb(var(--wx-tint)/0.08)]"
            >
              <Icon name="chevronLeft" size={18} />
            </button>
          )}

          {/* The whole brand block is the home control, not just the mark. */}
          <button
            type="button"
            onClick={onHome}
            aria-label={t(language, 'goHome')}
            title={t(language, 'goHome')}
            className="group flex min-w-0 flex-1 items-center gap-2 text-left"
          >
            {spec.glyph === 'cloud' ? (
              <Logo />
            ) : (
              <span className="grid h-[26px] w-[26px] shrink-0 place-items-center text-primary">
                <Icon name={spec.glyph} size={22} stroke={1.8} />
              </span>
            )}
            <span className="min-w-0 leading-[1.15]">
              <span
                className="block truncate text-[16.5px] font-bold tracking-[-0.02em] text-ink
                           transition-colors group-hover:text-primary"
              >
                Weather<span className="text-primary">GPT</span>
              </span>
              {spec.subtitle && (
                <span className="block truncate text-[10.5px] font-medium text-muted">
                  {t(language, spec.subtitle)}
                </span>
              )}
            </span>
          </button>

          <div className="flex shrink-0 items-center gap-0.5">
            <ConnectionDot state={socketState} language={language} />

            {/* The simulated-data chip is a Home-screen disclosure. On the
                assistant, where a back arrow and a subtitle already claim the
                row, it pushed the wordmark into an ellipsis — and the footer
                states the same thing on every screen. */}
            {dataSource === 'fixture' && !spec.back && (
              <span
                title={t(language, 'simulatedNote')}
                aria-label={t(language, 'simulated')}
                className="mr-0.5 hidden rounded-[var(--radius-pill)] bg-caution/15 px-1.5 py-px
                           text-[9px] font-bold tracking-wider text-caution-ink min-[360px]:inline"
              >
                SIM
              </span>
            )}

            <IconButton
              label={t(language, 'navAlerts')}
              onClick={() => onTrailing?.('alerts')}
              badge={alertCount}
            >
              <Icon name="bell" size={18} />
            </IconButton>

            <ProfileMenu onSignIn={onSignIn} />

            {/* Light is the default; this is the reader's override, remembered
                across visits. */}
            <IconButton
              label={t(language, 'appearance')}
              pressed={appearance === 'dark'}
              onClick={() => setAppearance(appearance === 'dark' ? 'light' : 'dark')}
            >
              <Icon name={appearance === 'dark' ? 'sun' : 'moon'} size={18} />
            </IconButton>

            <IconButton label={t(language, 'refresh')} onClick={onRefresh} disabled={refreshing}>
              <motion.span
                className="grid place-items-center"
                animate={refreshing ? { rotate: 360 } : { rotate: 0 }}
                transition={refreshing ? { duration: 0.9, repeat: Infinity, ease: 'linear' } : { duration: 0.2 }}
              >
                <Icon name="refresh" size={18} />
              </motion.span>
            </IconButton>

            {spec.trailing && (
              <IconButton label={t(language, 'tabSettings')} onClick={() => onTrailing?.(spec.trailing)}>
                <Icon name={spec.trailing} size={18} />
              </IconButton>
            )}
          </div>
        </div>

        {/* --- Row 2: location · role · language --------------------------
            Three pills of one kind, in the reference's own order. The role
            pill is a menu rather than a scrolling strip of seven buttons: at
            this width a strip pushed the page sideways, and the reference
            shows one pill. */}
        {spec.pills && (
          <div className="mt-2.5 flex min-w-0 items-center gap-1.5">
            <button
              type="button"
              onClick={onOpenLocation}
              title={t(language, 'changeLocation')}
              className="wx-pill min-w-0 flex-1 justify-start"
            >
              <Icon name="pin" size={13} className="text-primary" />
              <span className="min-w-0 truncate">{location?.name ?? '—'}</span>
              <Icon name="chevronRight" size={11} className="ml-auto text-faint" />
            </button>

            <Dropdown
              label={profileLabel(language, userType)}
              leading={<span aria-hidden="true" className="text-[12px] leading-none">{ROLE_ICONS[userType] ?? '🌤️'}</span>}
              ariaLabel={t(language, 'profile')}
              items={PROFILES.map((p) => ({ value: p, label: profileLabel(language, p), icon: ROLE_ICONS[p] }))}
              value={userType}
              onSelect={setUserType}
              className="min-w-0 flex-1"
            />

            <LanguagePicker />
          </div>
        )}

        {/* --- Row 3: search ---------------------------------------------- */}
        {spec.search && (
          <SearchField
            key={screen}
            placeholder={t(language, screen === 'map' ? 'searchOnMap' : 'searchAnything')}
            onSubmit={onSearch}
          />
        )}
      </div>
    </header>
  )
}

/**
 * The header's search field.
 *
 * On Home it takes a place *or* a question — which is what the reference's own
 * placeholder promises — so the submit handler is given the raw text and the
 * app decides which it was. Local state only; the field never holds the
 * application's location.
 */
function SearchField({ placeholder, onSubmit }) {
  const [value, setValue] = useState('')

  return (
    <form
      className="relative mt-2.5"
      onSubmit={(event) => {
        event.preventDefault()
        const text = value.trim()
        if (!text) return
        onSubmit?.(text)
        setValue('')
      }}
    >
      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint">
        <Icon name="search" size={15} />
      </span>
      <input
        type="search"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="wx-field pl-9"
      />
    </form>
  )
}

/** A 32px circular icon control. One shape for every icon in the bar. */
function IconButton({ label, onClick, disabled, pressed, badge = 0, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      aria-pressed={pressed}
      className="relative grid h-[30px] w-[30px] place-items-center rounded-full text-ink-soft transition
                 hover:bg-[rgb(var(--wx-tint)/0.09)] hover:text-primary disabled:opacity-40"
    >
      {children}
      {badge > 0 && (
        <span
          className="absolute right-0 top-0 min-w-[15px] rounded-full bg-danger px-[3px] text-center
                     text-[9px] font-bold leading-[15px] text-on-solid"
        >
          {badge > 9 ? '9+' : badge}
        </span>
      )}
    </button>
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
    // The emblem sits at x 0.204–0.860, y 0.072–0.620 of the square artwork,
    // above the wordmark. Rendering the file at 42px and offsetting by those
    // measurements puts the whole badge — and nothing else — in the 27px box.
    return (
      <span className="relative h-[27px] w-[27px] shrink-0 overflow-hidden rounded-lg">
        <img
          src={LOGO_SRC}
          alt=""
          aria-hidden="true"
          onError={() => setFailed(true)}
          className="absolute max-w-none"
          style={{ width: '42px', height: '42px', left: '-8.6px', top: '-1px' }}
          draggable="false"
        />
      </span>
    )
  }

  return (
    <span className="grid h-[27px] w-[27px] shrink-0 place-items-center text-primary">
      <Icon name="cloud" size={23} stroke={1.8} />
    </span>
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
    <span title={tone.label} className="mr-0.5 flex items-center px-0.5" role="status" aria-label={tone.label}>
      <span
        className={`h-[6px] w-[6px] rounded-full ${state === 'open' || state === 'polling' ? '' : 'pulse-alert'}`}
        style={{ background: tone.color }}
      />
    </span>
  )
}

function Dropdown({ label, leading, items, value, onSelect, ariaLabel, className = '' }) {
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
        onClick={() => setOpen((current) => !current)}
        className="wx-pill w-full justify-start"
      >
        {leading}
        <span className="min-w-0 truncate">{label}</span>
        <Icon name="chevronRight" size={11} className="ml-auto text-faint" />
      </button>

      <AnimatePresence>
        {open && (
          <motion.ul
            role="listbox"
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.16 }}
            className="glass glass-raised absolute left-0 z-40 mt-1.5 min-w-[10.5rem] overflow-hidden p-1"
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
                  className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[12px]
                              transition hover:bg-[rgb(var(--wx-tint)/0.09)] ${
                                item.value === value ? 'font-semibold text-primary' : 'text-ink-soft'
                              }`}
                >
                  {item.icon && <span aria-hidden="true">{item.icon}</span>}
                  <span className="min-w-0 truncate">{item.label}</span>
                </button>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  )
}
