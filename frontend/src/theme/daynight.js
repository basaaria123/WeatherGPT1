/**
 * Is it night where the reader is looking?
 *
 * One answer, derived once, consumed by the icon, the theme and the background
 * so none of them can disagree — the sun-at-midnight bug was exactly that
 * disagreement: the theme knew it was night and the glyph did not.
 *
 * The answer comes from the weather response already on screen, never from the
 * browser's own clock or timezone. A reader in Delhi looking at Vancouver must
 * see Vancouver's night, and no fetch happens to find that out.
 *
 * Two signals, in order of usefulness:
 *
 *   sunrise/sunset + timezone   the provider's own solar bounds for that place,
 *                               good for the whole day they describe
 *   is_day                      a boolean true only at the instant of the
 *                               reading, used when the bounds are missing
 *
 * `is_day` alone cannot hold a dashboard through the night: it is a snapshot,
 * and a reading taken at 17:00 still says "day" at 21:00. The bounds are what
 * make the state survive until sunrise.
 */

/** Minutes past local midnight, or null when the runtime has no such zone. */
function minutesNowAt(timezone, now) {
  if (!timezone) return null
  try {
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone: timezone,
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).formatToParts(now)
    const hour = Number(parts.find((p) => p.type === 'hour')?.value)
    const minute = Number(parts.find((p) => p.type === 'minute')?.value)
    if (!Number.isFinite(hour) || !Number.isFinite(minute)) return null
    // Some locales render midnight as 24; normalise so 24:10 is not 1450.
    return (hour % 24) * 60 + minute
  } catch {
    // An unknown IANA zone throws rather than guessing, which is the right
    // behaviour — we fall back to `is_day` instead of inventing a local time.
    return null
  }
}

/** Minutes past midnight from an ISO local stamp like `2026-09-08T18:24`. */
function minutesOf(stamp) {
  const match = /T(\d{2}):(\d{2})/.exec(String(stamp ?? ''))
  if (!match) return null
  return Number(match[1]) * 60 + Number(match[2])
}

export function isNightAt({ isDay, sunrise, sunset, timezone, now = new Date() } = {}) {
  const nowMinutes = minutesNowAt(timezone, now)
  const up = minutesOf(sunrise)
  const down = minutesOf(sunset)

  // The wrap is the whole point. Night is not "before sunrise" — at 00:30 that
  // test is also true of "before sunset", which is how a dashboard flips itself
  // back to daytime at midnight. Night is after sunset OR before sunrise, and
  // those are two different halves of the clock.
  if (nowMinutes !== null && up !== null && down !== null && up < down) {
    return nowMinutes >= down || nowMinutes < up
  }

  // No usable bounds: fall back to the provider's instant flag. Absent that,
  // assume day, which is what every caller defaulted to before this existed.
  return isDay === false
}

/** The same question, asked of a `/weather/current` response. */
export function isNightFor(currentData, now = new Date()) {
  const current = currentData?.current
  if (!current) return false
  return isNightAt({
    isDay: current.is_day,
    sunrise: current.sunrise,
    sunset: current.sunset,
    timezone: currentData?.location?.timezone,
    now,
  })
}
