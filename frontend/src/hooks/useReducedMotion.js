import { useEffect, useState } from 'react'

/**
 * Tracks `prefers-reduced-motion`.
 *
 * The CSS media query already neutralises transitions; this hook exists so
 * components can take a genuinely different path — a fade instead of a
 * particle build, a static gradient instead of a Three.js scene — rather than
 * running the same animation at zero duration.
 */
export function useReducedMotion() {
  const [reduced, setReduced] = useState(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  })

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return undefined
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = (event) => setReduced(event.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  return reduced
}
