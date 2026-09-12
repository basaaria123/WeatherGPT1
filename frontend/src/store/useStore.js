import { create } from 'zustand'
import { GUEST, clearSession, loadSession, saveSession } from '../auth/session'

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

// Profiles the selector used to offer. The backend still accepts them, so
// nothing breaks server-side — but a stored value the picker no longer lists
// would leave the role dropdown showing a blank label, so it is moved to the
// nearest profile that is still offered.
//
// `aviation` was here until it became a reading of its own; migrating it away
// now would take an aviation professional to the traveller's screen and give
// them a packing list.
const RETIRED_PROFILES = {
  commuter: 'driver',
  urban: 'driver',
  // Not retired — renamed. The backend answers to both, and the reading is
  // byte-for-byte the same one; this only keeps the picker from showing a
  // blank label for a key it no longer lists.
  fisherman: 'marine',
}

function migrateUserType(stored) {
  if (!stored) return stored
  return RETIRED_PROFILES[stored] ?? stored
}

const prefs = loadPrefs()

export const useStore = create((set, get) => ({
  // --- Session -------------------------------------------------------------
  sessionId: null,
  setSessionId: (sessionId) => set({ sessionId }),

  // --- Appearance ----------------------------------------------------------
  // Light by default. The weather still chooses the character of the theme —
  // the accent, the atmosphere, the pattern — and this chooses only whether
  // that character is painted on a bright ground or a dark one.
  appearance: prefs.appearance === 'dark' ? 'dark' : 'light',
  setAppearance: (appearance) => {
    const next = appearance === 'dark' ? 'dark' : 'light'
    savePrefs({ ...loadPrefs(), appearance: next })
    set({ appearance: next })
  },

  // --- Who is reading, and whether they have been set up -------------------
  // `onboarded` is remembered so a returning reader lands on the dashboard
  // rather than being asked the same three questions again.
  onboarded: prefs.onboarded ?? false,
  completeOnboarding: () => {
    savePrefs({ ...loadPrefs(), onboarded: true })
    set({ onboarded: true })
  },
  // Prototype identity — see src/auth/session.js. Guest is the default and the
  // whole product works in it; only SMS delivery needs a verified number.
  session: loadSession(),
  setSession: (session) => {
    saveSession(session)
    set({ session })
  },
  signOut: () => {
    clearSession()
    set({ session: GUEST, smsOptIn: false })
    savePrefs({ ...loadPrefs(), smsOptIn: false })
  },
  // SMS is opt-in, and off by default: an alert channel nobody asked for is
  // the wrong default even when it works.
  smsOptIn: prefs.smsOptIn ?? false,
  setSmsOptIn: (smsOptIn) => {
    savePrefs({ ...loadPrefs(), smsOptIn })
    set({ smsOptIn })
  },
  // --- Voice and audio ------------------------------------------------------
  // All three default on, because all three are things the reader has to press
  // before anything makes a sound. Nothing here can autoplay, so defaulting
  // them off would hide capabilities without protecting anyone from noise.
  spokenAdvice: prefs.spokenAdvice ?? true,
  setSpokenAdvice: (spokenAdvice) => {
    savePrefs({ ...loadPrefs(), spokenAdvice })
    set({ spokenAdvice })
  },
  audibleAlerts: prefs.audibleAlerts ?? true,
  setAudibleAlerts: (audibleAlerts) => {
    savePrefs({ ...loadPrefs(), audibleAlerts })
    set({ audibleAlerts })
  },
  voiceQuestions: prefs.voiceQuestions ?? true,
  setVoiceQuestions: (voiceQuestions) => {
    savePrefs({ ...loadPrefs(), voiceQuestions })
    set({ voiceQuestions })
  },

  smsSeverity: prefs.smsSeverity ?? 'high',
  setSmsSeverity: (smsSeverity) => {
    savePrefs({ ...loadPrefs(), smsSeverity })
    set({ smsSeverity })
  },

  // --- Preferences ---------------------------------------------------------
  language: prefs.language ?? 'en',
  userType: migrateUserType(prefs.userType) ?? 'general',
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
