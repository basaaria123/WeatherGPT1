/**
 * Severity presentation.
 *
 * Severity is never conveyed by colour alone: every consumer of this module
 * renders the icon and the label alongside the colour, so the meaning survives
 * for colour-blind users and in greyscale.
 */

export const SEVERITY = {
  Low: {
    key: 'Low',
    icon: '●',        // filled circle
    glyph: '✓',       // check
    color: 'var(--color-safe)',
    tint: 'rgb(52 211 153 / 0.13)',
    ring: 'rgb(52 211 153 / 0.42)',
  },
  Moderate: {
    key: 'Moderate',
    icon: '▲',        // triangle
    glyph: '!',
    color: 'var(--color-caution)',
    tint: 'rgb(251 191 36 / 0.13)',
    ring: 'rgb(251 191 36 / 0.42)',
  },
  High: {
    key: 'High',
    icon: '▲',
    glyph: '!!',
    color: 'var(--color-warning)',
    tint: 'rgb(251 146 60 / 0.15)',
    ring: 'rgb(251 146 60 / 0.48)',
  },
  Severe: {
    key: 'Severe',
    icon: '◆',        // diamond
    glyph: '!!!',
    color: 'var(--color-danger)',
    tint: 'rgb(244 63 94 / 0.16)',
    ring: 'rgb(244 63 94 / 0.55)',
  },
}

export const STATUS = {
  Safe: { color: 'var(--color-safe)', tint: 'rgb(52 211 153 / 0.13)', icon: '✓' },
  Caution: { color: 'var(--color-caution)', tint: 'rgb(251 191 36 / 0.13)', icon: '▲' },
  Avoid: { color: 'var(--color-danger)', tint: 'rgb(244 63 94 / 0.16)', icon: '✕' },
}

export const severityOf = (level) => SEVERITY[level] ?? SEVERITY.Low
export const statusOf = (status) => STATUS[status] ?? STATUS.Safe
export const isActionable = (level) => level === 'High' || level === 'Severe'
