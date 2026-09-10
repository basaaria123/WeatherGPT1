/**
 * One voice at a time.
 *
 * Three Listen controls sit on the dashboard now, and each owns its own audio
 * element. Without a referee, pressing the second while the first is playing
 * gives the reader two WeatherGPTs talking over each other — which is worse
 * than either of them alone, and impossible to recover from except by finding
 * and pressing whichever button started it.
 *
 * So playback is a claim on a single slot. Starting one stops whatever held it
 * before, wherever on the page that was. Deliberately a module-level value and
 * not React state: nothing renders from it, and a context would make every
 * consumer re-render on a press for no visible reason.
 */

let holder = null

/**
 * Take the slot, stopping whoever had it. `stop` is called when someone else
 * claims it, so it must be safe to run against already-stopped audio.
 */
export function claimPlayback(stop) {
  if (holder && holder !== stop) holder()
  holder = stop
}

/** Give the slot up, if it is still ours. */
export function releasePlayback(stop) {
  if (holder === stop) holder = null
}
