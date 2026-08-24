import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'

/** Location picker. Resolves through the backend geocoder — never a local list. */

const SUGGESTIONS = ['Vijayawada', 'Guwahati', 'Mumbai', 'Chennai', 'Kolkata', 'New Delhi', 'Kochi', 'Puri']

export default function LocationDialog({ open, onClose }) {
  const language = useStore((s) => s.language)
  const setLocation = useStore((s) => s.setLocation)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('idle') // idle | loading | error
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  useEffect(() => {
    if (open) {
      setQuery('')
      setError(null)
      setStatus('idle')
      // Delay focus until the entry animation has started, or iOS skips it.
      const timer = setTimeout(() => inputRef.current?.focus(), 120)
      return () => clearTimeout(timer)
    }
    return undefined
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (event) => event.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const resolve = async (name) => {
    const value = (name ?? query).trim()
    if (!value) return
    setStatus('loading')
    setError(null)
    try {
      const result = await api.geocode(value)
      setLocation(result.location)
      setStatus('idle')
      onClose()
    } catch (err) {
      setStatus('error')
      setError(err.message)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          className="fixed inset-0 z-50 flex items-start justify-center bg-[rgb(2_6_14/0.72)] p-4 pt-[12vh] backdrop-blur-sm"
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-label={t(language, 'changeLocation')}
        >
          <motion.div
            initial={{ opacity: 0, y: -14, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.98 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            onClick={(event) => event.stopPropagation()}
            className="glass glass-raised w-full max-w-md p-4"
          >
            <h2 className="mb-3 text-sm font-semibold text-ink">{t(language, 'changeLocation')}</h2>

            <form
              onSubmit={(event) => {
                event.preventDefault()
                resolve()
              }}
              className="flex gap-2"
            >
              <input
                ref={inputRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t(language, 'searchLocation')}
                aria-label={t(language, 'searchLocation')}
                className="min-w-0 flex-1 rounded-xl border border-white/12 bg-white/[0.05] px-3 py-2.5
                           text-sm text-ink placeholder:text-faint focus:border-primary/50 focus:outline-none"
              />
              <button
                type="submit"
                disabled={status === 'loading' || !query.trim()}
                className="shrink-0 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-[#04121d]
                           transition hover:brightness-110 disabled:opacity-40"
              >
                {status === 'loading' ? '…' : '→'}
              </button>
            </form>

            {error && (
              <p role="alert" className="mt-2.5 text-xs text-danger">
                {error}
              </p>
            )}

            <div className="mt-4">
              <p className="mb-2 text-[10px] uppercase tracking-[0.14em] text-faint">Popular</p>
              <div className="flex flex-wrap gap-1.5">
                {SUGGESTIONS.map((name) => (
                  <button
                    key={name}
                    type="button"
                    onClick={() => resolve(name)}
                    className="rounded-[var(--radius-pill)] border border-white/10 bg-white/[0.04] px-2.5 py-1
                               text-[11px] text-ink-soft transition hover:border-white/25 hover:bg-white/[0.1]"
                  >
                    {name}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
