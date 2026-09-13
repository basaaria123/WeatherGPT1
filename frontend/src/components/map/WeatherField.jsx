import { useCallback, useEffect, useRef } from 'react'
import { useMap, useMapEvents } from 'react-leaflet'

/**
 * The weather layer drawn as a surface rather than as sixteen dots.
 *
 * What this is, exactly, because it matters: an inverse-distance interpolation
 * of the same measured values the markers show. It is not a model output and
 * it is not observation everywhere — it is the readings we have, smoothed
 * between the places we have them for.
 *
 * That distinction is drawn on screen rather than left to a caption. The field
 * fades to nothing beyond `REACH_KM` of the nearest reading, so the colour stops
 * where the evidence stops instead of confidently painting the Bay of Bengal a
 * shade of green. Where you can see colour, a station influenced it.
 *
 * Drawn on a canvas in Leaflet's overlay pane, under the markers and above the
 * basemap, and redrawn on move, zoom and resize. Sixteen points against a
 * coarse grid is a few thousand distance calculations — cheap enough to redraw
 * on every frame of a pan, which is why it tracks rather than lags.
 */

// How far a single reading is allowed to speak for. Beyond this the field is
// transparent: the map says "no reading here" by showing the basemap.
const REACH_KM = 420
// Grid pitch in screen pixels. Small enough to read as a surface, large enough
// that a pan stays smooth on a phone.
const CELL = 9
// The field is a wash the markers and the basemap read through, never a paint
// layer that hides the geography underneath it.
const MAX_ALPHA = 0.62

export default function WeatherField({ entries, layer, step, valueAt }) {
  const map = useMap()
  const canvasRef = useRef(null)
  const frameRef = useRef(0)

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas || !map) return
    const size = map.getSize()
    const dpr = Math.min(window.devicePixelRatio || 1, 2)

    if (canvas.width !== size.x * dpr || canvas.height !== size.y * dpr) {
      canvas.width = size.x * dpr
      canvas.height = size.y * dpr
      canvas.style.width = `${size.x}px`
      canvas.style.height = `${size.y}px`
    }
    const ctx = canvas.getContext('2d')
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, size.x, size.y)

    // Only places that actually have a value for this layer at this step. A
    // place whose provider sent nothing must not pull the surface towards zero.
    const points = []
    for (const entry of entries ?? []) {
      const value = valueAt(entry, layer, step)
      if (typeof value !== 'number') continue
      const p = map.latLngToContainerPoint([entry.latitude, entry.longitude])
      points.push({ x: p.x, y: p.y, value })
    }
    if (points.length === 0) return

    // Metres per pixel at this latitude and zoom, so REACH_KM means the same
    // distance on the ground whatever the reader has zoomed to.
    const centre = map.getCenter()
    const metresPerPixel =
      (40075016.686 * Math.abs(Math.cos((centre.lat * Math.PI) / 180))) /
      (256 * 2 ** map.getZoom())
    const reachPx = (REACH_KM * 1000) / Math.max(metresPerPixel, 1)
    const reachSq = reachPx * reachPx

    const paint = colourResolver(layer)

    for (let y = 0; y < size.y; y += CELL) {
      for (let x = 0; x < size.x; x += CELL) {
        const cx = x + CELL / 2
        const cy = y + CELL / 2

        let weighted = 0
        let weights = 0
        let nearestSq = Infinity
        for (const point of points) {
          const dx = cx - point.x
          const dy = cy - point.y
          const dSq = dx * dx + dy * dy
          if (dSq < nearestSq) nearestSq = dSq
          if (dSq > reachSq) continue
          // +1 keeps the weight finite at the station itself.
          const weight = 1 / (dSq + 1)
          weighted += point.value * weight
          weights += weight
        }
        if (weights === 0) continue

        // Confidence falls with distance from the nearest reading and reaches
        // zero at the edge of its reach, so the surface has a soft boundary
        // rather than a hard disc.
        const nearness = 1 - Math.sqrt(nearestSq) / reachPx
        if (nearness <= 0) continue

        ctx.fillStyle = paint(weighted / weights)
        ctx.globalAlpha = MAX_ALPHA * Math.pow(nearness, 1.6)
        ctx.fillRect(x, y, CELL, CELL)
      }
    }
    ctx.globalAlpha = 1
  }, [map, entries, layer, step, valueAt])

  // One redraw per animation frame however many events arrive.
  const schedule = useCallback(() => {
    cancelAnimationFrame(frameRef.current)
    frameRef.current = requestAnimationFrame(draw)
  }, [draw])

  useMapEvents({ move: schedule, zoom: schedule, resize: schedule, viewreset: schedule })
  useEffect(() => {
    schedule()
    return () => cancelAnimationFrame(frameRef.current)
  }, [schedule])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 z-[350]"
    />
  )
}

/**
 * The layer's own ramp, resolved to something a canvas can paint.
 *
 * The ramp returns CSS custom properties — `var(--color-safe)` — because every
 * other consumer of it is an SVG or a DOM node. A canvas cannot read those, so
 * they are resolved against the document once per draw, which also means the
 * surface follows a theme change without knowing a theme exists.
 *
 * Between two stops the colour is mixed rather than stepped: a banded map reads
 * as a choropleth of regions that do not exist, and the point of a surface is
 * that weather does not have edges.
 */
function colourResolver(layer) {
  const root = getComputedStyle(document.documentElement)
  const cache = new Map()
  const rgbOf = (css) => {
    if (cache.has(css)) return cache.get(css)
    const name = /var\((--[a-z-]+)\)/i.exec(css)?.[1]
    const raw = (name ? root.getPropertyValue(name) : css).trim() || '#888888'
    cache.set(css, hexToRgb(raw))
    return cache.get(css)
  }

  const stops = (layer.stops ?? []).map((stop) => ({ at: stop.at, rgb: rgbOf(stop.color) }))
  if (stops.length === 0) {
    return (value) => {
      const [r, g, b] = rgbOf(layer.ramp(value))
      return `rgb(${r} ${g} ${b})`
    }
  }

  return (value) => {
    let lower = stops[0]
    let upper = stops[stops.length - 1]
    for (let i = 0; i < stops.length - 1; i += 1) {
      if (value >= stops[i].at && value <= stops[i + 1].at) {
        lower = stops[i]
        upper = stops[i + 1]
        break
      }
    }
    if (value <= stops[0].at) { lower = upper = stops[0] }
    if (value >= stops[stops.length - 1].at) { lower = upper = stops[stops.length - 1] }
    const span = upper.at - lower.at
    const t = span > 0 ? (value - lower.at) / span : 0
    const mix = (a, b) => Math.round(a + (b - a) * t)
    return `rgb(${mix(lower.rgb[0], upper.rgb[0])} ${mix(lower.rgb[1], upper.rgb[1])} ${mix(lower.rgb[2], upper.rgb[2])})`
  }
}

function hexToRgb(value) {
  const hex = value.replace('#', '').trim()
  if (hex.length === 3) {
    return [0, 1, 2].map((i) => parseInt(hex[i] + hex[i], 16))
  }
  if (hex.length >= 6) {
    return [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16))
  }
  const nums = value.match(/\d+/g)
  return nums && nums.length >= 3 ? nums.slice(0, 3).map(Number) : [136, 136, 136]
}
