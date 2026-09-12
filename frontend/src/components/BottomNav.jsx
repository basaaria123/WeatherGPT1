import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'

/**
 * The app's primary navigation.
 *
 * Five destinations, each answering one question the reader actually has:
 *
 *   Home      what should I do now?
 *   AI        ask me anything about the weather
 *   Map       where is the risk?
 *   Alerts    what needs my attention?
 *   Forecast  what is coming?
 *
 * Everything else — profile, role, language, notification and voice
 * preferences, climate history — is reachable from the header rather than
 * competing for one of these five slots. A destination here is a *question*,
 * not a settings page.
 *
 * Fixed to the bottom because that is where a thumb is on a phone, and padded
 * for the home indicator so the last row of a scrolling page is never trapped
 * underneath it.
 */

const ICONS = {
  home: (
    <>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5.5 9.4V20a.9.9 0 0 0 .9.9h3.4v-5.3h4.4V21h3.4a.9.9 0 0 0 .9-.9V9.4" />
    </>
  ),
  ai: (
    <>
      <path d="M12 2.6 13.9 8 19.4 9.9 13.9 11.8 12 17.2 10.1 11.8 4.6 9.9 10.1 8z" />
      <path d="M18.4 15.1l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z" />
    </>
  ),
  map: (
    <>
      <path d="M9.2 3.4 3 5.9v14.7l6.2-2.5 5.6 2.5 6.2-2.5V3.4l-6.2 2.5z" />
      <path d="M9.2 3.4v14.7M14.8 5.9v14.7" />
    </>
  ),
  alerts: (
    <>
      <path d="M12 2.8a6.3 6.3 0 0 1 6.3 6.3c0 4.9 1.9 6.5 1.9 6.5H3.8s1.9-1.6 1.9-6.5A6.3 6.3 0 0 1 12 2.8z" />
      <path d="M9.9 19a2.2 2.2 0 0 0 4.2 0" />
    </>
  ),
  forecast: (
    <>
      <rect x="3.2" y="4.6" width="17.6" height="16.2" rx="2.2" />
      <path d="M3.2 9.4h17.6M8 2.6v4M16 2.6v4" />
    </>
  ),
}

const TABS = [
  { id: 'home', label: 'navHome', icon: 'home' },
  { id: 'ai', label: 'navAI', icon: 'ai' },
  { id: 'map', label: 'navMap', icon: 'map' },
  { id: 'alerts', label: 'navAlerts', icon: 'alerts' },
  { id: 'forecast', label: 'navForecast', icon: 'forecast' },
]

export default function BottomNav({ screen, onNavigate }) {
  const language = useStore((s) => s.language)
  // The badge counts what is live now, which is the same list the Alerts
  // screen renders — one source, so the number on the tab can never disagree
  // with the screen it points at.
  const alertCount = useStore((s) => s.alerts.length)

  return (
    <nav
      aria-label={t(language, 'navPrimary')}
      className="fixed inset-x-0 bottom-0 z-40 border-t border-[rgb(var(--wx-tint)/0.14)]
                 bg-[rgb(var(--wx-surface)/0.92)] backdrop-blur-md
                 pb-[max(env(safe-area-inset-bottom),0.35rem)]"
    >
      <ul className="mx-auto flex w-full max-w-lg items-stretch">
        {TABS.map((tab) => {
          const active = screen === tab.id
          const badge = tab.id === 'alerts' ? alertCount : 0
          return (
            <li key={tab.id} className="min-w-0 flex-1">
              <button
                type="button"
                onClick={() => onNavigate(tab.id)}
                aria-current={active ? 'page' : undefined}
                className={`relative flex min-h-[3.25rem] w-full flex-col items-center justify-center gap-[3px]
                            px-1 pt-1.5 transition-colors
                            ${active ? 'text-[rgb(var(--wx-tint))]' : 'text-faint hover:text-ink'}`}
              >
                <span className="relative">
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={active ? 2 : 1.6}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    {ICONS[tab.icon]}
                  </svg>
                  {badge > 0 && (
                    <span
                      className="absolute -right-2 -top-1.5 min-w-[1.05rem] rounded-full bg-danger px-1
                                 text-center text-[10px] font-bold leading-[1.05rem] text-white"
                    >
                      {badge > 9 ? '9+' : badge}
                    </span>
                  )}
                </span>
                <span className="w-full truncate text-center text-[10.5px] font-medium leading-none">
                  {t(language, tab.label)}
                </span>
                {/* The active marker is a shape as well as a colour, so the
                    current tab is still identifiable in greyscale. */}
                {active && (
                  <span className="absolute inset-x-[28%] top-0 h-[2.5px] rounded-full bg-[rgb(var(--wx-tint))]" />
                )}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
