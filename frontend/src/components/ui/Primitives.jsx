import { levelLabel } from '../../i18n/ui'
import { useStore } from '../../store/useStore'
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
      className={`glass min-w-0 scroll-mt-24 p-4 ${className}`}
    >
      {(title || action) && (
        <header className="mb-3 flex items-center justify-between gap-3">
          {title && (
            <h2 className="wx-eyebrow min-w-0 truncate">{title}</h2>
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
  // `level` is the backend's English enum. Every pill that showed it raw put
  // "Low" beside a translated verdict, so the localised word is the default and
  // an explicit `label` still wins.
  const language = useStore((s) => s.language)
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-[var(--radius-pill)] font-semibold ${
        compact ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-[3px] text-[10.5px]'
      }`}
      style={{ background: tone.tint, color: tone.ink }}
    >
      <span aria-hidden="true">{tone.icon}</span>
      <span>{label ?? levelLabel(language, level)}</span>
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
      style={{ background: tone.tint, color: tone.ink }}
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
      className={`wx-pill disabled:cursor-not-allowed disabled:opacity-45
        ${active ? 'wx-pill-on' : ''}`}
    >
      {children}
    </button>
  )
}

/**
 * One reading: a quiet label over a loud value.
 *
 * The reference's whole statistics block is this shape repeated — a small
 * muted label, then the number in bold with its unit at label weight beside it.
 * Keeping it in one component is what stops the nine on the conditions card
 * drifting from the four on a forecast row.
 */
export function Metric({ label, value, unit, icon }) {
  // Callers omit missing metrics entirely; this is a guard, not a placeholder.
  if (value === null || value === undefined || value === '') return null
  return (
    <div className="min-w-0">
      <div className="flex min-w-0 items-center gap-1">
        {icon}
        <span className="truncate text-[9.5px] font-semibold uppercase tracking-[0.07em] text-muted">
          {label}
        </span>
      </div>
      <div className="mt-[3px] truncate text-[15px] font-bold leading-tight tracking-[-0.01em] text-ink">
        {value}
        {unit ? <span className="ml-[2px] text-[10px] font-semibold text-muted">{unit}</span> : null}
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
          className="mt-3 rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.15)] bg-[rgb(var(--wx-tint)/0.06)] px-3 py-1.5
                     text-xs font-medium text-ink transition hover:border-[rgb(var(--wx-tint)/0.30)] hover:bg-[rgb(var(--wx-tint)/0.12)]"
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
    <h2 className="wx-eyebrow">{children}</h2>
  )
}

/**
 * A row of tabs, drawn the way the reference draws them: the chosen one is a
 * solid blue pill, the rest are white with a hairline. Not a segmented control
 * in a tray — the reference's tabs sit directly on the page.
 *
 * `items` are `{ id, label, count }`; a count is appended in brackets, which is
 * how the reference shows "Active (2)".
 */
export function Tabs({ items, value, onChange, ariaLabel, idPrefix = 'tab' }) {
  return (
    <div role="tablist" aria-label={ariaLabel} className="flex min-w-0 gap-1.5">
      {items.map((item) => {
        const active = value === item.id
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            id={`${idPrefix}-${item.id}`}
            aria-selected={active}
            aria-controls={`${idPrefix}-panel-${item.id}`}
            onClick={() => onChange(item.id)}
            className={`wx-pill min-w-0 flex-1 justify-center px-2 py-[7px] text-[12px]
                        ${active ? 'wx-pill-on' : 'wx-pill-off'}`}
          >
            <span className="min-w-0 truncate">
              {item.label}
              {item.count ? ` (${item.count})` : ''}
            </span>
          </button>
        )
      })}
    </div>
  )
}
