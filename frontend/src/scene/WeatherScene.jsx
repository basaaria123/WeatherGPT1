import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { motion } from 'framer-motion'
import { Suspense, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { dampingFor } from '../theme/weatherTheme'

/**
 * Full-bleed animated background that reacts to the current condition.
 *
 * Three guardrails keep it from competing with the content it sits behind:
 * a CSS gradient always paints first (so a WebGL failure degrades to a
 * deliberate-looking background rather than a black box), reduced-motion skips
 * the canvas entirely, and geometry counts stay low with a clamped DPR.
 */

// Long enough to be a change of weather rather than a change of screen, short
// enough that a reader who switched location on purpose is not left waiting.
const SKY_FADE_MS = 6000

const PALETTES = {
  clear:  { top: '#0a2647', bottom: '#050d1a', cloud: '#7dd3fc', cloudOpacity: 0.1,  clouds: 5,  rain: 0 },
  cloudy: { top: '#0b2440', bottom: '#050d1a', cloud: '#94a3b8', cloudOpacity: 0.2,  clouds: 9,  rain: 0 },
  rain:   { top: '#0a1c30', bottom: '#03080f', cloud: '#64748b', cloudOpacity: 0.26, clouds: 10, rain: 900 },
  storm:  { top: '#0a1526', bottom: '#02060c', cloud: '#475569', cloudOpacity: 0.34, clouds: 12, rain: 1400 },
  fog:    { top: '#132538', bottom: '#0a1622', cloud: '#cbd5e1', cloudOpacity: 0.2,  clouds: 12, rain: 0 },
  snow:   { top: '#12263d', bottom: '#060e1a', cloud: '#e2e8f0', cloudOpacity: 0.22, clouds: 9,  rain: 400 },
  heat:   { top: '#2a1a10', bottom: '#0b0a14', cloud: '#fbbf24', cloudOpacity: 0.1,  clouds: 3,  rain: 0 },
}

/**
 * What each sky becomes after dark.
 *
 * `top`/`bottom` deepen towards indigo; `stars` and `moon` say how much of the
 * night is actually visible through the weather. A clear night gets both, a
 * thunderstorm gets neither — the cloud deck is the point, and a moon shining
 * through storm cover would be a picture of weather that is not happening.
 * Nothing here is large or bright: it is the ground the dashboard sits on.
 */
const NIGHT = {
  clear:  { top: '#122a52', bottom: '#050b18', stars: 120, moon: 1 },
  cloudy: { top: '#101f3c', bottom: '#050a16', stars: 45,  moon: 0.62 },
  rain:   { top: '#0b1830', bottom: '#03070f', stars: 0,   moon: 0.28 },
  storm:  { top: '#0a1224', bottom: '#02050b', stars: 0,   moon: 0 },
  fog:    { top: '#101c2e', bottom: '#070e1a', stars: 18,  moon: 0.3 },
  snow:   { top: '#0e2038', bottom: '#050c18', stars: 40,  moon: 0.5 },
  heat:   { top: '#1d1424', bottom: '#080711', stars: 55,  moon: 0.5 },
}

export function nightFor(scene) {
  return NIGHT[scene] ?? NIGHT.clear
}

/** Blend two `#rrggbb` colours. Used only for the sky, never for text. */
function mix(from, to, amount) {
  const parse = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
  const [ar, ag, ab] = parse(from)
  const [br, bg, bb] = parse(to)
  const channel = (a, b) => Math.round(a + (b - a) * amount).toString(16).padStart(2, '0')
  return `#${channel(ar, br)}${channel(ag, bg)}${channel(ab, bb)}`
}

/**
 * The sky, leaning towards what is coming.
 *
 * A dashboard that only ever paints the present hour tells a reader nothing
 * about the rain due at four. So when the next few hours hold something worse,
 * the ground colour drifts a third of the way towards it — cooler and greyer
 * ahead of the rain, darker ahead of the storm.
 *
 * Colour only, and deliberately: the *particles* stay keyed to what is actually
 * falling now. Drawing rain over "partly cloudy" would be the same lie as a sun
 * at midnight, and a lean in the palette is a mood where falling water is a
 * claim.
 */
const LEAN = 0.34

export function skyFor(scene, { night = false, approaching } = {}) {
  const base = paletteFor(scene, night)
  if (!approaching || approaching === scene) return base
  const ahead = paletteFor(approaching, night)
  return { ...base, top: mix(base.top, ahead.top, LEAN), bottom: mix(base.bottom, ahead.bottom, LEAN) }
}

export function paletteFor(scene, night = false) {
  const base = PALETTES[scene] ?? PALETTES.clear
  if (!night) return base
  const after = nightFor(scene)
  return { ...base, top: after.top, bottom: after.bottom }
}

/** Soft radial sprite texture, generated once — no external image to load. */
function useCloudTexture(color) {
  return useMemo(() => {
    const size = 128
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = size
    const ctx = canvas.getContext('2d')
    const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
    gradient.addColorStop(0, color)
    gradient.addColorStop(0.45, color)
    gradient.addColorStop(1, 'rgba(0,0,0,0)')
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, size, size)
    const texture = new THREE.CanvasTexture(canvas)
    texture.needsUpdate = true
    return texture
  }, [color])
}

function Clouds({ count, color, opacity, speed = 1 }) {
  const texture = useCloudTexture(color)
  const group = useRef()
  const { viewport } = useThree()

  const sprites = useMemo(
    () =>
      Array.from({ length: count }).map((_, index) => ({
        key: index,
        x: (Math.random() - 0.5) * 26,
        y: 1.5 + Math.random() * 6,
        z: -6 - Math.random() * 10,
        scale: 5 + Math.random() * 9,
        drift: 0.1 + Math.random() * 0.22,
      })),
    [count],
  )

  useFrame((_, delta) => {
    if (!group.current) return
    const limit = Math.max(16, viewport.width)
    group.current.children.forEach((sprite, index) => {
      sprite.position.x += sprites[index].drift * delta * speed
      // Wrap around instead of respawning, so density stays constant.
      if (sprite.position.x > limit) sprite.position.x = -limit
    })
  })

  return (
    <group ref={group}>
      {sprites.map((sprite) => (
        <sprite key={sprite.key} position={[sprite.x, sprite.y, sprite.z]} scale={sprite.scale}>
          <spriteMaterial
            map={texture}
            transparent
            opacity={opacity}
            depthWrite={false}
            blending={THREE.NormalBlending}
          />
        </sprite>
      ))}
    </group>
  )
}

function Rain({ count, colour = '#7dd3fc', slant = 0.25, speed = 14 }) {
  const ref = useRef()
  const positions = useMemo(() => {
    const array = new Float32Array(count * 3)
    for (let i = 0; i < count; i += 1) {
      array[i * 3] = (Math.random() - 0.5) * 34
      array[i * 3 + 1] = Math.random() * 26 - 8
      array[i * 3 + 2] = -2 - Math.random() * 12
    }
    return array
  }, [count])

  useFrame((_, delta) => {
    const geometry = ref.current
    if (!geometry) return
    const array = geometry.attributes.position.array
    const step = delta * speed
    for (let i = 0; i < count; i += 1) {
      array[i * 3 + 1] -= step
      array[i * 3] += step * slant
      if (array[i * 3 + 1] < -10) {
        array[i * 3 + 1] = 18
        array[i * 3] = (Math.random() - 0.5) * 34
      }
    }
    geometry.attributes.position.needsUpdate = true
  })

  return (
    <points>
      <bufferGeometry ref={ref}>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color={colour} size={0.09} transparent opacity={0.5} sizeAttenuation depthWrite={false} />
    </points>
  )
}

/** Occasional lightning: a brief ambient spike, never a rapid strobe. */
function Lightning({ strength = 1 }) {
  const light = useRef()
  const next = useRef(2 + Math.random() * 4)
  const flash = useRef(0)

  useFrame((state, delta) => {
    next.current -= delta
    if (next.current <= 0) {
      flash.current = 0.16
      // Rarer as well as dimmer when the risk is high: a severe storm gets a
      // quieter sky, not a strobe over the advice about it.
      next.current = (4 + Math.random() * 7) / Math.max(0.2, strength)
    }
    if (flash.current > 0) {
      flash.current -= delta
      if (light.current) light.current.intensity = 2.4 * strength * Math.max(0, flash.current / 0.16)
    } else if (light.current) {
      light.current.intensity = 0
    }
  })

  return <ambientLight ref={light} color="#e0f2fe" intensity={0} />
}

/** Rising heat shimmer: slow vertical motes, not a distortion shader. */
function HeatHaze({ count = 220 }) {
  const ref = useRef()
  const positions = useMemo(() => {
    const array = new Float32Array(count * 3)
    for (let i = 0; i < count; i += 1) {
      array[i * 3] = (Math.random() - 0.5) * 30
      array[i * 3 + 1] = Math.random() * 20 - 9
      array[i * 3 + 2] = -3 - Math.random() * 9
    }
    return array
  }, [count])

  useFrame((state, delta) => {
    const geometry = ref.current
    if (!geometry) return
    const array = geometry.attributes.position.array
    const time = state.clock.elapsedTime
    for (let i = 0; i < count; i += 1) {
      array[i * 3 + 1] += delta * 0.55
      array[i * 3] += Math.sin(time * 0.7 + i) * delta * 0.16
      if (array[i * 3 + 1] > 13) array[i * 3 + 1] = -9
    }
    geometry.attributes.position.needsUpdate = true
  })

  return (
    <points>
      <bufferGeometry ref={ref}>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color="#fbbf24" size={0.12} transparent opacity={0.24} sizeAttenuation depthWrite={false} />
    </points>
  )
}

/**
 * A star field, in two layers that breathe out of phase.
 *
 * Two `points` objects rather than one: twinkling per star would need a custom
 * shader, and two slow opacity oscillations read as the same thing for two
 * draw calls and one material write per frame. They do not move — drifting
 * stars are a rotating sky, which is a different and much busier idea.
 */
function Stars({ count }) {
  const layers = useMemo(
    () =>
      [0, 1].map((layer) => {
        const size = Math.round(count / 2)
        const array = new Float32Array(size * 3)
        for (let i = 0; i < size; i += 1) {
          array[i * 3] = (Math.random() - 0.5) * 40
          // Weighted to the upper frame, where the dashboard is not, but
          // reaching a little below the horizon line so the sky does not stop
          // in a straight edge behind the first card.
          array[i * 3 + 1] = -2 + Math.random() * 17
          array[i * 3 + 2] = -14 - Math.random() * 10
        }
        return { array, layer }
      }),
    [count],
  )

  const materials = useRef([])
  useFrame((state) => {
    const time = state.clock.elapsedTime
    materials.current.forEach((material, index) => {
      // Floor kept well above zero: a star that fades out entirely reads as a
      // rendering glitch rather than as twinkling.
      if (material) material.opacity = 0.5 + 0.18 * Math.sin(time * 0.32 + index * Math.PI)
    })
  })

  return (
    <>
      {layers.map(({ array, layer }) => (
        <points key={layer}>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" args={[array, 3]} />
          </bufferGeometry>
          <pointsMaterial
            ref={(material) => { materials.current[layer] = material }}
            color="#e8f0ff"
            size={layer === 0 ? 0.13 : 0.095}
            transparent
            opacity={0.5}
            sizeAttenuation
            depthWrite={false}
          />
        </points>
      ))}
    </>
  )
}

/**
 * The moon: one soft disc and one wider glow, both from the same generated
 * texture the clouds use. No image is loaded, and `strength` is how much of it
 * survives the weather in front of it.
 */
function Moon({ strength = 1 }) {
  const disc = useCloudTexture('#eef4ff')
  const glow = useCloudTexture('#9dc0f0')
  return (
    <group position={[8.5, 7.4, -13]}>
      <sprite scale={7}>
        <spriteMaterial map={glow} transparent opacity={0.14 * strength} depthWrite={false} blending={THREE.AdditiveBlending} />
      </sprite>
      <sprite scale={1.5}>
        <spriteMaterial map={disc} transparent opacity={0.72 * strength} depthWrite={false} />
      </sprite>
    </group>
  )
}

function SceneContents({ scene, light = false, night = false, riskLevel }) {
  const palette = paletteFor(scene, night)
  const after = nightFor(scene)
  const damp = dampingFor(riskLevel)
  // Pale clouds vanish against a bright sky, so a light theme darkens them and
  // leans on opacity instead. Counts and motion are unchanged.
  const cloudColor = light ? '#8fa8bd' : night ? '#3d5680' : palette.cloud
  const cloudOpacity = light ? Math.min(0.5, palette.cloudOpacity + 0.22) : palette.cloudOpacity
  return (
    <>
      <ambientLight intensity={night ? 0.22 : 0.35} />
      {/* Behind the clouds, so a cloudy night covers its own moon. */}
      {night && after.stars > 0 && <Stars count={after.stars} />}
      {night && after.moon > 0 && <Moon strength={after.moon} />}
      <Clouds
        count={Math.round(palette.clouds * damp.motion)}
        color={cloudColor}
        opacity={cloudOpacity}
        speed={(scene === 'storm' ? 2.4 : 1) * damp.motion}
      />
      {palette.rain > 0 && scene !== 'snow' && (
        <Rain
          count={Math.round(palette.rain * damp.motion)}
          slant={scene === 'storm' ? 0.5 : 0.2}
          speed={(scene === 'storm' ? 20 : 13) * damp.motion}
        />
      )}
      {scene === 'snow' && (
        <Rain count={Math.round(palette.rain * damp.motion)} colour="#e2e8f0" slant={0.06} speed={2.4} />
      )}
      {scene === 'storm' && <Lightning strength={damp.flash} />}
      {scene === 'heat' && <HeatHaze />}
    </>
  )
}

export default function WeatherScene({
  scene = 'clear',
  intensity = 1,
  light = false,
  night = false,
  riskLevel,
  approaching,
  className = '',
}) {
  const reduced = useReducedMotion()
  const [webglFailed, setWebglFailed] = useState(false)
  const palette = paletteFor(scene, night)

  // On a light theme the scene's own dark palette would fight the interface,
  // so the ground comes from the theme variables and only the weather motion
  // (clouds, rain) stays scene-specific.
  const sky = skyFor(scene, { night, approaching })
  const gradient = light
    ? 'radial-gradient(120% 90% at 50% -10%, var(--wx-bg-deep) 0%, var(--wx-bg) 58%, var(--wx-bg) 100%)'
    : `radial-gradient(120% 90% at 50% -10%, ${sky.top} 0%, ${sky.bottom} 62%, var(--wx-bg-deep) 100%)`

  // Browsers cannot interpolate one gradient into another, so a CSS transition
  // on `background` snaps however long it is set to. Two stacked layers can
  // cross-fade, which is what makes cloudy → rain → storm a drift the reader
  // never catches happening rather than a cut.
  const previous = useRef(gradient)
  const settled = previous.current
  if (settled !== gradient) {
    // Held until the incoming layer has finished; the outgoing one sits under
    // it, fully covered by the time it is swapped.
    setTimeout(() => { previous.current = gradient }, SKY_FADE_MS)
  }

  return (
    <div className={`pointer-events-none fixed inset-0 -z-10 ${className}`} aria-hidden="true">
      {/* Always painted: the canvas is an enhancement on top of this. The
          outgoing sky sits beneath the incoming one and the top layer fades in
          over several seconds, which is what makes sunset, sunrise and an
          approaching front all read as drift rather than as a cut. */}
      <div className="absolute inset-0" style={{ background: settled }} />
      <motion.div
        key={gradient}
        className="absolute inset-0"
        initial={{ opacity: settled === gradient ? 1 : 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: SKY_FADE_MS / 1000, ease: 'easeInOut' }}
        style={{ background: gradient }}
      />

      {/* Stars for readers who have asked not to be moved. The canvas below is
          skipped entirely for them, so without this a clear night would be a
          bare gradient; the CSS paints them once and never animates. */}
      {night && reduced && <div className="wx-still-stars absolute inset-0" />}

      {!reduced && !webglFailed && (
        <Suspense fallback={null}>
          <Canvas
            camera={{ position: [0, 0, 12], fov: 55 }}
            dpr={[1, 1.6]}
            gl={{ antialias: false, alpha: true, powerPreference: 'low-power' }}
            style={{ opacity: (light ? 0.6 : 0.85) * intensity }}
            onCreated={({ gl }) => gl.setClearColor(0x000000, 0)}
            fallback={null}
            onError={() => setWebglFailed(true)}
          >
            <SceneContents scene={scene} light={light} night={night} riskLevel={riskLevel} />
          </Canvas>
        </Suspense>
      )}

      {/* Vignette keeps text legible over the busiest part of the scene. */}
      <div
        className="absolute inset-0"
        style={{ background: 'var(--wx-vignette)' }}
      />
    </div>
  )
}
