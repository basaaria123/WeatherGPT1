import { motion } from 'framer-motion'
import { severityOf, statusOf } from './severity'

/* Shared building blocks. Keeping them here means spacing, radii and the glass
   treatment stay consistent instead of being re-invented per panel. */

export function Panel({ title, action, children, className = '', delay = 0, id }) {
  return (
    <motion.section
      id={id}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay, ease: [0.22, 1, 0.36, 1] }}
      /* min-w-0 lets the panel shrink inside a grid; without it a grid item
         sizes to its widest child and pushes the whole page sideways. */
      className={`glass min-w-0 scroll-mt-24 p-4 sm:p-5 ${className}`}
    >
      {(title || action) && (
        <header className="mb-3 flex items-center justify-between gap-3">
          {title && (
            <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
              {title}
            </h2>
          )}
          {action}
        </header>
      )}
      {children}
    </motion.section>
  )
}

export function SeverityPill({ level, label, score, compact = false }) {
  const tone = severityOf(level)
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-[var(--radius-pill)] border font-semibold ${
        compact ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-[11px]'
      }`}
      style={{ background: tone.tint, borderColor: tone.ring, color: tone.color }}
    >
      <span aria-hidden="true">{tone.icon}</span>
      <span>{label ?? level}</span>
      {score !== undefined && score !== null && (
        <span className="opacity-70">{score}</span>
      )}
    </span>
  )
}

export function StatusPill({ status, label }) {
  const tone = statusOf(status)
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-[var(--radius-pill)] px-2 py-0.5 text-[11px] font-semibold"
      style={{ background: tone.tint, color: tone.color }}
    >
      <span aria-hidden="true">{tone.icon}</span>
      {label ?? status}
    </span>
  )
}

export function Chip({ children, onClick, active = false, disabled = false, title }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-pressed={active}
      className={`rounded-[var(--radius-pill)] border px-3 py-1.5 text-xs font-medium transition
        disabled:cursor-not-allowed disabled:opacity-45
        ${
          active
            ? 'border-primary/60 bg-primary/15 text-primary'
            : 'border-white/10 bg-white/[0.04] text-ink-soft hover:border-white/25 hover:bg-white/[0.09]'
        }`}
    >
      {children}
    </button>
  )
}

export function Metric({ label, value, unit }) {
  // Callers omit missing metrics entirely; this is a guard, not a placeholder.
  if (value === null || value === undefined || value === '') return null
  return (
    <div className="min-w-0">
      <div className="truncate text-[11px] uppercase tracking-[0.1em] text-faint">{label}</div>
      <div className="mt-0.5 truncate text-sm font-semibold text-ink">
        {value}
        {unit ? <span className="ml-0.5 text-[11px] font-normal text-muted">{unit}</span> : null}
      </div>
    </div>
  )
}

export function Skeleton({ className = '' }) {
  return <div className={`shimmer rounded-lg ${className}`} aria-hidden="true" />
}

export function LoadingBlock({ label, lines = 3 }) {
  return (
    <div role="status" aria-live="polite" className="space-y-2.5">
      <span className="sr-only">{label}</span>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton key={index} className={`h-3 ${index === lines - 1 ? 'w-2/3' : 'w-full'}`} />
      ))}
    </div>
  )
}

export function ErrorState({ title, message, onRetry, retryLabel = 'Try again' }) {
  return (
    <div role="alert" className="rounded-xl border border-danger/25 bg-danger/[0.07] p-4">
      <p className="text-sm font-semibold text-ink">{title}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-[var(--radius-pill)] border border-white/15 bg-white/[0.06] px-3 py-1.5
                     text-xs font-medium text-ink transition hover:border-white/30 hover:bg-white/[0.12]"
        >
          {retryLabel}
        </button>
      )}
    </div>
  )
}

export function EmptyState({ message, icon = '○' }) {
  return (
    <div className="flex flex-col items-center gap-2 py-7 text-center">
      <span aria-hidden="true" className="text-2xl text-faint">{icon}</span>
      <p className="max-w-[26ch] text-xs leading-relaxed text-muted">{message}</p>
    </div>
  )
}

export function SectionTitle({ children }) {
  return (
    <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">{children}</h2>
  )
}
