/**
 * The profiles WeatherGPT offers, in one place.
 *
 * Order matters — it is the order the onboarding grid and the header selector
 * both present — and the ids are the values the backend reasons about, so a
 * role added here without a matching reading in `role_intel.py`, `advisory.py`
 * and the hazard rules table would be a label the product cannot honour.
 *
 * Labels are not here: they live in `ui.js` under `profiles`, translated with
 * the rest of the interface chrome.
 */
export const ROLES = [
  { id: 'farmer', icon: '🌾' },
  { id: 'marine', icon: '🎣' },
  { id: 'aviation', icon: '✈️' },
  { id: 'disaster', icon: '🚨' },
  { id: 'smart_city', icon: '🏙️' },
  { id: 'researcher', icon: '🔬' },
  { id: 'student', icon: '🎓' },
  { id: 'driver', icon: '🚗' },
  { id: 'outdoor_worker', icon: '🦺' },
  { id: 'household', icon: '🏠' },
  { id: 'traveler', icon: '🧳' },
  { id: 'caregiver', icon: '👨‍👩‍👧' },
  // Last, and deliberately: it is the default rather than a profession, and
  // putting it first implies the twelve above are variations on it.
  { id: 'general', icon: '🌤️' },
]

export const ROLE_IDS = ROLES.map((role) => role.id)

export const ROLE_ICONS = Object.fromEntries(ROLES.map((role) => [role.id, role.icon]))
