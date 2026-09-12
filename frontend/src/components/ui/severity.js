/**
 * Severity presentation.
 *
 * Severity is never conveyed by colour alone: every consumer of this module
 * renders the icon and the label alongside the colour, so the meaning survives
 * for colour-blind users and in greyscale.
 */

/**
 * The wash and the hairline are mixed from the band's own colour rather than
 * written out, so a palette change moves all twelve values at once and no
 * severity can keep a colour the theme no longer uses.
 *
 * `color` is what the band looks like; `ink` is what it looks like *as text*.
 * They differ only for the caution band, whose fill colour is unreadable at
 * text sizes on white — see the note in weatherTheme.js.
 */
const wash = (token) => `color-mix(in srgb, var(${token}) 11%, transparent)`
const edge = (token) => `color-mix(in srgb, var(${token}) 38%, transparent)`

export const SEVERITY = {
  Low: {
    key: 'Low',
    icon: '●',        // filled circle
    glyph: '✓',       // check
    color: 'var(--color-safe)',
    ink: 'var(--color-safe)',
    tint: wash('--color-safe'),
    ring: edge('--color-safe'),
  },
  Moderate: {
    key: 'Moderate',
    icon: '▲',        // triangle
    glyph: '!',
    color: 'var(--color-caution)',
    ink: 'var(--color-caution-ink)',
    tint: wash('--color-caution'),
    ring: edge('--color-caution'),
  },
  High: {
    key: 'High',
    icon: '▲',
    glyph: '!!',
    color: 'var(--color-warning)',
    ink: 'var(--color-warning)',
    tint: wash('--color-warning'),
    ring: edge('--color-warning'),
  },
  Severe: {
    key: 'Severe',
    icon: '◆',        // diamond
    glyph: '!!!',
    color: 'var(--color-danger)',
    ink: 'var(--color-danger)',
    tint: wash('--color-danger'),
    ring: edge('--color-danger'),
  },
}

export const STATUS = {
  Safe: { color: 'var(--color-safe)', ink: 'var(--color-safe)', tint: wash('--color-safe'), icon: '✓' },
  Caution: { color: 'var(--color-caution)', ink: 'var(--color-caution-ink)', tint: wash('--color-caution'), icon: '▲' },
  Avoid: { color: 'var(--color-danger)', ink: 'var(--color-danger)', tint: wash('--color-danger'), icon: '✕' },
}

export const severityOf = (level) => SEVERITY[level] ?? SEVERITY.Low
export const statusOf = (status) => STATUS[status] ?? STATUS.Safe
export const isActionable = (level) => level === 'High' || level === 'Severe'
