import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  LANGUAGE_CATALOG,
  LANGUAGE_COUNT_LABEL,
  bestMatchIndex,
  findLanguage,
  groupLanguages,
  searchLanguages,
  withServerLanguages,
} from '../i18n/languages'
import { isLatinText, safeNative } from '../i18n/scriptSupport'
import { t } from '../i18n/ui'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { useStore } from '../store/useStore'

/**
 * The language selector.
 *
 * A list of thirty-five languages cannot be a plain dropdown — it would be a
 * column taller than the dashboard, and the screenshot that prompted this work
 * showed exactly that, a panel lying across the risk score. So the panel is
 * fixed in size and scrolls inside itself: a heading, a search box, a grouped
 * list with a bounded height, and a footer. Nothing behind it moves.
 *
 * Everything on screen is derived from `LANGUAGE_CATALOG`. There is no list of
 * thirty-five buttons here, only one row component and a loop.
 *
 * Changing the language writes one field in the store. It does not touch the
 * location, the profile, the session or any weather state, so the dashboard
 * keeps its numbers and simply re-labels them.
 */

const GROUP_LABEL_KEYS = {
  popular: 'groupPopular',
  north: 'groupNorth',
  south: 'groupSouth',
  east: 'groupEast',
  community: 'groupCommunity',
}

const GROUP_ICONS = { popular: '⭐' }

// Stable id so the search field can point at the highlighted row.
const LIST_ID = 'language-listbox'

export default function LanguagePicker({ className = '' }) {
  const language = useStore((s) => s.language)
  const setLanguage = useStore((s) => s.setLanguage)
  const capabilities = useStore((s) => s.capabilities)

  const reduced = useReducedMotion()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [cursor, setCursor] = useState(0)

  const rootRef = useRef(null)
  const triggerRef = useRef(null)
  const searchRef = useRef(null)
  const listRef = useRef(null)

  const place = usePlacement(triggerRef, open)

  // The server is the authority on which languages it can actually answer in.
  const catalog = useMemo(
    () => withServerLanguages(LANGUAGE_CATALOG, capabilities?.languages),
    [capabilities?.languages],
  )

  const matches = useMemo(() => searchLanguages(catalog, query), [catalog, query])
  const groups = useMemo(() => groupLanguages(matches), [matches])
  // Flattened in render order, so the arrow keys walk the list the eye sees.
  const flat = useMemo(() => groups.flatMap((group) => group.items), [groups])

  const selected = findLanguage(language)
  const selectedNative = safeNative(selected)
  const supported = catalog.find((entry) => entry.id === language)?.translation ?? selected.translation

  useEffect(() => {
    if (!open) return undefined
    const onPointer = (event) => {
      if (rootRef.current && !rootRef.current.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onPointer)
    return () => document.removeEventListener('mousedown', onPointer)
  }, [open])

  // Opening always starts from a clean, unfiltered list.
  useEffect(() => {
    if (!open) return
    setQuery('')
    // Only on a pointer-and-keyboard screen: focusing here on a phone throws
    // up the keyboard over the list the user came to read.
    if (window.matchMedia('(min-width: 640px)').matches) {
      window.requestAnimationFrame(() => searchRef.current?.focus())
    }
  }, [open])

  // The highlight follows the query — and with no query, it rests on the
  // language already in use, so opening and pressing Enter changes nothing.
  useEffect(() => {
    setCursor(
      query ? bestMatchIndex(flat, query) : Math.max(0, flat.findIndex((entry) => entry.id === language)),
    )
  }, [query, flat, language])

  useEffect(() => {
    if (!open || !listRef.current) return
    const row = listRef.current.querySelector('[data-active="true"]')
    row?.scrollIntoView({ block: 'nearest' })
  }, [cursor, open])

  const choose = (id) => {
    setLanguage(id)
    setOpen(false)
  }

  const onKeyDown = (event) => {
    if (event.key === 'Escape') {
      setOpen(false)
      return
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      if (flat.length === 0) return
      const step = event.key === 'ArrowDown' ? 1 : -1
      setCursor((index) => (index + step + flat.length) % flat.length)
      return
    }
    if (event.key === 'Enter' && flat[cursor]) {
      event.preventDefault()
      choose(flat[cursor].id)
    }
  }

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        ref={triggerRef}
        type="button"
        aria-label={t(language, 'language')}
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-1 rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.10)] bg-[rgb(var(--wx-tint)/0.05)]
                   px-2.5 py-1.5 text-xs font-medium text-ink transition hover:border-[rgb(var(--wx-tint)/0.25)] hover:bg-[rgb(var(--wx-tint)/0.1)]"
      >
        {/* The trigger names the language in its own script — a Telugu speaker
            looks for తెలుగు, not for "Telugu". */}
        <span className="sm:hidden">{selected.short}</span>
        <span className="hidden sm:inline">{selectedNative || selected.english}</span>
        <span aria-hidden="true" className="text-[10px] text-faint">▾</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            /* The panel still appears and disappears when motion is reduced;
               it just does not travel to get there. */
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: -6, scale: 0.98 }}
            animate={reduced ? { opacity: 1 } : { opacity: 1, y: 0, scale: 1 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: reduced ? 0.01 : 0.16 }}
            onKeyDown={onKeyDown}
            style={place}
            /* Placed against the viewport rather than the trigger, because at
               320px the trigger sits close enough to the right edge that a
               panel hung from it runs off the left of the screen. `usePlacement`
               keeps it under the trigger, inside both edges, and no taller than
               the space actually below it — so the list scrolls and the page
               never does. */
            /* The glass gradient alone is see-through, which was fine for a
               six-row menu and is not fine for a panel this tall — the risk
               score behind it would read straight through the list. Painting
               the theme's own scrim underneath keeps the frosted look while
               making the text opaque, in the light weather themes as well as
               the dark ones. */
            className="glass glass-raised fixed z-50 flex flex-col overflow-hidden
                       bg-[rgb(var(--wx-scrim)/0.985)] p-0 backdrop-blur-2xl"
          >
            <div className="flex items-center gap-1.5 border-b border-[rgb(var(--wx-tint)/0.08)] px-3 py-2">
              <span aria-hidden="true" className="text-[13px]">🌐</span>
              <span
                className={`text-[11px] font-semibold text-muted ${
                  isLatinText(t(language, 'chooseLanguage')) ? 'uppercase tracking-[0.12em]' : ''
                }`}
              >
                {t(language, 'chooseLanguage')}
              </span>
            </div>

            <div className="px-2.5 pb-2 pt-2">
              <input
                ref={searchRef}
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t(language, 'searchLanguage')}
                aria-label={t(language, 'searchLanguage')}
                /* The field filters a list that is already on screen, so it is
                   a combobox over that listbox and the highlighted row is
                   announced through it rather than by moving focus. */
                role="combobox"
                aria-expanded="true"
                aria-controls={LIST_ID}
                aria-activedescendant={flat[cursor] ? `${LIST_ID}-${flat[cursor].id}` : undefined}
                autoComplete="off"
                spellCheck="false"
                className="w-full rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.10)] bg-[rgb(var(--wx-tint)/0.05)]
                           px-3 py-1.5 text-xs text-ink outline-none transition placeholder:text-faint
                           focus:border-primary/50 focus:bg-[rgb(var(--wx-tint)/0.08)]"
              />
            </div>

            <ul
              ref={listRef}
              id={LIST_ID}
              role="listbox"
              aria-label={t(language, 'language')}
              className="scroll-y min-h-0 flex-1 overflow-y-auto px-1.5 pb-1.5"
            >
              {flat.length === 0 && (
                <li className="px-2.5 py-6 text-center text-xs text-faint">{t(language, 'noLanguageFound')}</li>
              )}

              {groups.map((group) => (
                <li key={group.id} role="group" aria-label={t(language, GROUP_LABEL_KEYS[group.id])}>
                  <div
                    aria-hidden="true"
                    className={`px-2.5 pb-1 pt-2 text-[10px] font-semibold text-faint ${
                      isLatinText(t(language, GROUP_LABEL_KEYS[group.id]))
                        ? 'uppercase tracking-[0.14em]'
                        : 'text-[11px]'
                    }`}
                  >
                    {GROUP_ICONS[group.id] ? `${GROUP_ICONS[group.id]} ` : ''}
                    {t(language, GROUP_LABEL_KEYS[group.id])}
                  </div>
                  <ul role="presentation">
                    {group.items.map((entry) => (
                      <LanguageRow
                        key={entry.id}
                        entry={entry}
                        uiLanguage={language}
                        selected={entry.id === language}
                        active={flat[cursor]?.id === entry.id}
                        onSelect={choose}
                      />
                    ))}
                  </ul>
                </li>
              ))}
            </ul>

            <div className="border-t border-[rgb(var(--wx-tint)/0.08)] px-3 py-2">
              <VoiceReadiness entry={selected} supported={supported} uiLanguage={language} />
              <div className="mt-1.5 text-[10px] text-faint">
                {LANGUAGE_COUNT_LABEL} {t(language, 'regionalLanguages')}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/**
 * One selectable language.
 *
 * The English name leads because it is the one every reader can at least
 * pronounce; the native name follows when the browser owns a font for it, and
 * is simply absent when it does not — an empty box would tell the user less
 * than nothing. Languages the backend cannot yet write in are marked so, right
 * on the row, rather than letting the user discover it from an English answer.
 */
function LanguageRow({ entry, uiLanguage, selected, active, onSelect }) {
  const native = safeNative(entry)
  return (
    <li>
      <button
        id={`${LIST_ID}-${entry.id}`}
        type="button"
        role="option"
        aria-selected={selected}
        data-active={active ? 'true' : 'false'}
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => onSelect(entry.id)}
        title={entry.translation ? entry.english : `${entry.english} — ${t(uiLanguage, 'answersInEnglish')}`}
        className={`flex min-h-[40px] w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs
                    transition sm:min-h-0 sm:py-1.5 ${
                      selected
                        ? 'bg-primary/12 text-primary'
                        : `text-ink-soft hover:bg-[rgb(var(--wx-tint)/0.09)] ${
                            active ? 'bg-[rgb(var(--wx-tint)/0.06)]' : ''
                          }`
                    }`}
      >
        {/* A transparent tick would still be read out and still be copied
            with the text, so the unselected rows get an empty box instead. */}
        <span aria-hidden="true" className="w-3 shrink-0 text-[11px] text-primary">
          {selected ? '✓' : ''}
        </span>
        <span className="min-w-0 flex-1 truncate font-medium">{entry.english}</span>
        {/* Indic scripts sit low and need the extra pixel and the extra leading
            to stay legible next to Latin text at this size. */}
        {native && (
          <span className="max-w-[45%] shrink-0 truncate text-[13px] leading-normal text-muted">{native}</span>
        )}
        {!entry.translation && (
          <span
            aria-label={t(uiLanguage, 'answersInEnglish')}
            className="shrink-0 rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.12)] px-1.5
                       py-px text-[9px] font-semibold tracking-wide text-faint"
          >
            EN
          </span>
        )}
      </button>
    </li>
  )
}

/**
 * What voice can and cannot do in the chosen language, stated plainly.
 *
 * These are indicators, not controls: the microphone lives in the chat panel
 * and the speaker on each answer. Showing a button here that only looked like
 * it worked would be worse than showing nothing, so this reports the state the
 * server and the catalogue actually report and offers no shortcut.
 */
function VoiceReadiness({ entry, supported, uiLanguage }) {
  const capabilities = useStore((s) => s.capabilities)
  const canSpeak = Boolean(capabilities?.voice_input_available) && entry.voice && supported
  const canListen = Boolean(capabilities?.voice_output_available) && entry.voice && supported

  if (!entry.voice || !supported) {
    return (
      <div className="flex items-center gap-1.5 text-[10px] text-faint">
        <span aria-hidden="true">🎙️</span>
        <span className="truncate">{t(uiLanguage, 'voiceNotInLanguage')}</span>
      </div>
    )
  }

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px]">
      <span className={`flex items-center gap-1 ${canSpeak ? 'text-primary/85' : 'text-faint'}`}>
        <span aria-hidden="true">🎙️</span>
        <span className="truncate">{t(uiLanguage, 'speakToApp')}</span>
      </span>
      <span className={`flex items-center gap-1 ${canListen ? 'text-primary/85' : 'text-faint'}`}>
        <span aria-hidden="true">🔊</span>
        <span className="truncate">{t(uiLanguage, 'listenToAnswers')}</span>
      </span>
    </div>
  )
}

/**
 * Where the panel goes.
 *
 * It hangs under the trigger and is pulled back inside whichever viewport edge
 * it would otherwise cross — on a 320px screen the trigger is close enough to
 * the right edge that a right-aligned panel would start off-screen. Its height
 * is whatever room is left below the trigger, capped, so the list scrolls
 * inside the panel and the dashboard behind it never moves.
 */
function usePlacement(triggerRef, open) {
  const [style, setStyle] = useState(null)

  useEffect(() => {
    if (!open) return undefined

    const measure = () => {
      const trigger = triggerRef.current
      if (!trigger) return
      const rect = trigger.getBoundingClientRect()
      const vw = window.innerWidth
      const vh = window.innerHeight
      const margin = 8
      const width = Math.min(304, vw - margin * 2)
      // Right-aligned to the trigger, then nudged left until it fits.
      const right = Math.min(Math.max(vw - rect.right, margin), vw - width - margin)
      const top = rect.bottom + 6
      setStyle({
        top,
        right,
        width,
        maxHeight: Math.max(180, Math.min(vh - top - 12, 416)),
      })
    }

    measure()
    window.addEventListener('resize', measure)
    // The header is sticky, so scrolling does not move the trigger; an address
    // bar collapsing on a phone does, and that arrives as a resize too.
    return () => window.removeEventListener('resize', measure)
  }, [open, triggerRef])

  return style ?? { top: -9999, right: 0, width: 304 }
}
