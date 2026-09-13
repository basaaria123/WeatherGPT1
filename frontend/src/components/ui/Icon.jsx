/**
 * The icon set.
 *
 * One stroke weight, one 24-box, one join style — which is the whole reason
 * this file exists. The interface previously drew its icons as emoji and as
 * typographic glyphs (◎ ↻ ☾ ✦), and a row of those is a row of six different
 * drawing styles at six different optical weights. The reference uses a single
 * outlined set throughout, so this is it.
 *
 * Every path is drawn inside a 24×24 box with `fill="none"`, so the colour is
 * whatever `currentColor` is where it is used and the weight is set by the
 * caller. Nothing here carries a colour of its own.
 */

const PATHS = {
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.6-3.6" /></>,
  pin: <><path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11z" /><circle cx="12" cy="10" r="2.6" /></>,
  leaf: <><path d="M20 4c0 9-5.4 13-10.5 13A4.5 4.5 0 0 1 5 12.5C5 7.4 11 4 20 4z" /><path d="M4 20c3-5.6 6.6-8.6 11-10.5" /></>,
  globe: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.4 2.6 3.6 5.6 3.6 9s-1.2 6.4-3.6 9c-2.4-2.6-3.6-5.6-3.6-9S9.6 5.6 12 3z" /></>,
  bell: <><path d="M18 8.6a6 6 0 1 0-12 0c0 5-2 6.4-2 6.4h16s-2-1.4-2-6.4z" /><path d="M10.2 19a2 2 0 0 0 3.6 0" /></>,
  moon: <path d="M20 14.4A8.4 8.4 0 0 1 9.6 4 8.6 8.6 0 1 0 20 14.4z" />,
  sun: <><circle cx="12" cy="12" r="4.2" /><path d="M12 2.6v2.2M12 19.2v2.2M2.6 12h2.2M19.2 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M18.7 5.3l-1.6 1.6M6.9 17.1l-1.6 1.6" /></>,
  refresh: <><path d="M20.4 12a8.4 8.4 0 1 1-2.5-6" /><path d="M20.6 4.2v5h-5" /></>,
  user: <><circle cx="12" cy="8.4" r="3.8" /><path d="M4.8 20.2a7.6 7.6 0 0 1 14.4 0" /></>,
  chevronDown: <path d="m6.5 9.5 5.5 5.4 5.5-5.4" />,
  chevronRight: <path d="m9.5 5.6 6 6.4-6 6.4" />,
  chevronLeft: <path d="m14.5 5.6-6 6.4 6 6.4" />,
  mic: <><rect x="9" y="2.8" width="6" height="11.4" rx="3" /><path d="M5.4 11.4a6.6 6.6 0 0 0 13.2 0M12 18v3.2" /></>,
  send: <path d="M4 12 20.4 4.4 13.6 20.4l-2.2-6.6z" />,
  speaker: <><path d="M4.6 9.4h3.2L12.8 5v14l-5-4.4H4.6z" /><path d="M16.2 9.2a4 4 0 0 1 0 5.6M18.8 6.6a7.6 7.6 0 0 1 0 10.8" /></>,
  sparkle: <><path d="m12 3 1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" /><path d="m18.4 15.6.7 1.9 1.9.7-1.9.7-.7 1.9-.7-1.9-1.9-.7 1.9-.7z" /></>,
  clock: <><circle cx="12" cy="12" r="8.6" /><path d="M12 7v5.4l3.4 2" /></>,
  warning: <><path d="M12 3.6 21.2 19.6H2.8z" /><path d="M12 9.6v4.6M12 17.2v.1" /></>,
  shield: <><path d="M12 3 19.4 6v6c0 4.4-3 7.6-7.4 9-4.4-1.4-7.4-4.6-7.4-9V6z" /><path d="m8.8 12 2.2 2.2 4.2-4.4" /></>,
  layers: <><path d="m12 3 8.6 4.6L12 12.2 3.4 7.6z" /><path d="m3.4 12.4 8.6 4.6 8.6-4.6M3.4 16.9 12 21.5l8.6-4.6" /></>,
  sliders: <><path d="M4 7h10M18 7h2M4 17h2M10 17h10" /><circle cx="16" cy="7" r="2" /><circle cx="8" cy="17" r="2" /></>,
  calendar: <><rect x="3.4" y="5" width="17.2" height="15.6" rx="2.4" /><path d="M3.4 9.8h17.2M8.4 2.8v4.4M15.6 2.8v4.4" /></>,
  droplet: <path d="M12 3.2c3.4 3.9 6 7 6 10a6 6 0 0 1-12 0c0-3 2.6-6.1 6-10z" />,
  wind: <><path d="M3.6 8.4h9.2a2.8 2.8 0 1 0-2.8-2.8" /><path d="M3.6 12.6h13a2.8 2.8 0 1 1-2.8 2.8M3.6 16.8h6.6" /></>,
  gauge: <><path d="M4.2 18a9 9 0 1 1 15.6 0" /><path d="m12 13.6 3.8-3.8" /></>,
  thermometer: <><path d="M14.2 13.6V5.4a2.2 2.2 0 1 0-4.4 0v8.2a4.4 4.4 0 1 0 4.4 0z" /></>,
  eye: <><path d="M2.6 12S6.4 5.8 12 5.8 21.4 12 21.4 12 17.6 18.2 12 18.2 2.6 12 2.6 12z" /><circle cx="12" cy="12" r="3" /></>,
  cloud: <path d="M7.4 18.4a4.4 4.4 0 0 1-.6-8.8 5.8 5.8 0 0 1 11.2 1.2 3.8 3.8 0 0 1-.6 7.6z" />,
  info: <><circle cx="12" cy="12" r="8.8" /><path d="M12 11v5.4M12 7.9v.1" /></>,
  dots: <><circle cx="12" cy="5" r="1.3" /><circle cx="12" cy="12" r="1.3" /><circle cx="12" cy="19" r="1.3" /></>,
  play: <path d="M8 5.4 18.6 12 8 18.6z" />,
  pause: <><path d="M9 5.4v13.2M15 5.4v13.2" /></>,
  check: <path d="m5 12.8 4.6 4.6L19 6.8" />,
  trend: <><path d="M3.4 16.4 9 10.8l3.6 3.6 7.4-7.4" /><path d="M15.4 7h5v5" /></>,
}

export const ICON_NAMES = Object.keys(PATHS)

/**
 * @param name   one of ICON_NAMES
 * @param size   pixel box; the reference uses 14–16 inline, 18 in controls and
 *               22 in the bottom bar
 * @param stroke line weight; 1.7 is the reference's resting weight and 2.1 the
 *               weight it uses to mark an active item
 */
export default function Icon({ name, size = 16, stroke = 1.7, className = '', style }) {
  const path = PATHS[name]
  if (!path) return null
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={`shrink-0 ${className}`}
      style={style}
    >
      {path}
    </svg>
  )
}
