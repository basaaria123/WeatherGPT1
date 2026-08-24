import { create } from 'zustand'

/**
 * Global UI state.
 *
 * Deliberately holds only things several panels need at once: the session, the
 * chosen location, language and profile, and the live alert feed. Panel-local
 * loading and error state stays in the panel that owns it.
 */

const STORAGE_KEY = 'weathergpt:prefs'

function loadPrefs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function savePrefs(prefs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
  } catch {
    /* private mode, quota, blocked storage — preferences are a nicety */
  }
}

const prefs = loadPrefs()

export const useStore = create((set, get) => ({
  // --- Session -------------------------------------------------------------
  sessionId: null,
  setSessionId: (sessionId) => set({ sessionId }),

  // --- Preferences ---------------------------------------------------------
  language: prefs.language ?? 'en',
  userType: prefs.userType ?? 'general',
  responseMode: 'normal',
  setLanguage: (language) => {
    savePrefs({ ...loadPrefs(), language })
    set({ language })
  },
  setUserType: (userType) => {
    savePrefs({ ...loadPrefs(), userType })
    set({ userType })
  },
  setResponseMode: (responseMode) => set({ responseMode }),

  // --- Location ------------------------------------------------------------
  location: prefs.location ?? { name: 'Vijayawada', admin1: 'Andhra Pradesh' },
  setLocation: (location) => {
    savePrefs({ ...loadPrefs(), location })
    set({ location })
  },

  // --- Backend capabilities (from /config, /health) ------------------------
  capabilities: null,
  setCapabilities: (capabilities) => set({ capabilities }),
  dataSource: 'live',
  setDataSource: (dataSource) => set({ dataSource }),

  // --- Live alerts ---------------------------------------------------------
  alerts: [],
  socketState: 'connecting', // connecting | open | closed
  setSocketState: (socketState) => set({ socketState }),
  setAlerts: (alerts) => set({ alerts }),
  pushAlert: (alert) => {
    const existing = get().alerts
    // Alerts arrive over the socket and via snapshots; de-duplicate by id.
    if (existing.some((a) => a.id === alert.id)) return
    set({ alerts: [alert, ...existing].slice(0, 40), lastAlertId: alert.id })
  },
  lastAlertId: null,

  // --- Current conditions, shared by the hero card and the 3D scene --------
  current: null,
  risk: null,
  setConditions: ({ current, risk }) => set({ current, risk }),

  // --- Demo mode -----------------------------------------------------------
  demoOpen: false,
  setDemoOpen: (demoOpen) => set({ demoOpen }),

  // --- Map focus, driven by "View affected area" links ---------------------
  mapFocus: null,
  setMapFocus: (mapFocus) => set({ mapFocus }),
}))

export const severityRank = { Low: 0, Moderate: 1, High: 2, Severe: 3 }
