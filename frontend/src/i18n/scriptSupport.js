/**
 * Does this browser actually have a glyph for a script?
 *
 * WeatherGPT lists languages written in a dozen scripts. A machine with no
 * Odia font renders ଓଡ଼ିଆ as a row of empty boxes, which is worse than reading
 * "Odia" — a name in tofu is a name the user cannot recognise at all.
 *
 * So before showing a native name we ask the canvas whether it can draw it. A
 * character with no glyph falls back to the font's .notdef box, and every
 * .notdef box in a given font is the same picture. Drawing the character and a
 * private-use codepoint — which no font covers — and comparing the two bitmaps
 * therefore answers the question directly.
 *
 * The answer is cached per script sample: the probe runs at most once per
 * script per page load, and the fallback is always the English name.
 */

// A codepoint in the Private Use Area. Nothing in a normal font stack covers
// it, so whatever it draws is this font's "I have no glyph" picture.
const NOTDEF = ''

const cache = new Map()

let context

function probeContext() {
  if (context !== undefined) return context
  try {
    const canvas = document.createElement('canvas')
    canvas.width = 64
    canvas.height = 32
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    if (ctx) {
      ctx.font = '24px sans-serif'
      ctx.textBaseline = 'top'
    }
    context = ctx ?? null
  } catch {
    context = null
  }
  return context
}

function draw(ctx, text) {
  ctx.clearRect(0, 0, 64, 32)
  ctx.fillText(text, 2, 2)
  return ctx.getImageData(0, 0, 64, 32).data
}

function identical(a, b) {
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i += 1) if (a[i] !== b[i]) return false
  return true
}

function blank(pixels) {
  for (let i = 3; i < pixels.length; i += 4) if (pixels[i] !== 0) return false
  return true
}

/**
 * True when the browser can draw `sample`.
 *
 * Unknown counts as supported: if the probe cannot run — no canvas, a hardened
 * browser, a headless renderer — showing the native name is the behaviour the
 * app already had, and hiding names on a guess would be the bigger regression.
 */
export function canRenderScript(sample) {
  if (!sample) return false
  const key = sample.codePointAt(0)
  const cached = cache.get(key)
  if (cached !== undefined) return cached

  let supported = true
  try {
    // Chrome and Safari implement the text-coverage half of this check, which
    // is both cheaper and more accurate than reading pixels back.
    if (typeof document !== 'undefined' && document.fonts?.check) {
      supported = document.fonts.check('24px sans-serif', sample)
    }
    if (supported) {
      const ctx = probeContext()
      if (ctx) {
        const drawn = draw(ctx, sample)
        supported = !blank(drawn) && !identical(drawn, draw(ctx, NOTDEF))
      }
    }
  } catch {
    supported = true
  }

  cache.set(key, supported)
  return supported
}

const ASCII_ONLY = /^[ -~]*$/

/**
 * True for plain Latin text.
 *
 * Uppercasing and letter-spacing are Latin typographic devices. Applied to
 * Devanagari or Telugu they do nothing useful and actively harm legibility,
 * because the extra tracking pulls a conjunct apart into loose glyphs. Labels
 * check this before taking those classes.
 */
export function isLatinText(value) {
  return ASCII_ONLY.test(value ?? '')
}

/**
 * The native name when it will render, otherwise an empty string — callers
 * then show the English name alone rather than a row of boxes. Latin native
 * names are always safe and skip the probe.
 */
export function safeNative(entry) {
  if (!entry?.native) return ''
  if (ASCII_ONLY.test(entry.native)) return entry.native
  return canRenderScript(entry.native[0]) ? entry.native : ''
}
