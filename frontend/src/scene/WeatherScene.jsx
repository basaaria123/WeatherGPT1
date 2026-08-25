import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Suspense, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { useReducedMotion } from '../hooks/useReducedMotion'

/**
 * Full-bleed animated background that reacts to the current condition.
 *
 * Three guardrails keep it from competing with the content it sits behind:
 * a CSS gradient always paints first (so a WebGL failure degrades to a
 * deliberate-looking background rather than a black box), reduced-motion skips
 * the canvas entirely, and geometry counts stay low with a clamped DPR.
 */

const PALETTES = {
  clear:  { top: '#0a2647', bottom: '#050d1a', cloud: '#7dd3fc', cloudOpacity: 0.1,  clouds: 5,  rain: 0 },
  cloudy: { top: '#0b2440', bottom: '#050d1a', cloud: '#94a3b8', cloudOpacity: 0.2,  clouds: 9,  rain: 0 },
  rain:   { top: '#0a1c30', bottom: '#03080f', cloud: '#64748b', cloudOpacity: 0.26, clouds: 10, rain: 900 },
  storm:  { top: '#0a1526', bottom: '#02060c', cloud: '#475569', cloudOpacity: 0.34, clouds: 12, rain: 1400 },
  fog:    { top: '#132538', bottom: '#0a1622', cloud: '#cbd5e1', cloudOpacity: 0.2,  clouds: 12, rain: 0 },
  snow:   { top: '#12263d', bottom: '#060e1a', cloud: '#e2e8f0', cloudOpacity: 0.22, clouds: 9,  rain: 400 },
  heat:   { top: '#2a1a10', bottom: '#0b0a14', cloud: '#fbbf24', cloudOpacity: 0.1,  clouds: 3,  rain: 0 },
}

export function paletteFor(scene) {
  return PALETTES[scene] ?? PALETTES.clear
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
function Lightning() {
  const light = useRef()
  const next = useRef(2 + Math.random() * 4)
  const flash = useRef(0)

  useFrame((state, delta) => {
    next.current -= delta
    if (next.current <= 0) {
      flash.current = 0.16
      next.current = 4 + Math.random() * 7
    }
    if (flash.current > 0) {
      flash.current -= delta
      if (light.current) light.current.intensity = 2.4 * Math.max(0, flash.current / 0.16)
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

function SceneContents({ scene, light = false }) {
  const palette = paletteFor(scene)
  // Pale clouds vanish against a bright sky, so a light theme darkens them and
  // leans on opacity instead. Counts and motion are unchanged.
  const cloudColor = light ? '#8fa8bd' : palette.cloud
  const cloudOpacity = light ? Math.min(0.5, palette.cloudOpacity + 0.22) : palette.cloudOpacity
  return (
    <>
      <ambientLight intensity={0.35} />
      <Clouds
        count={palette.clouds}
        color={cloudColor}
        opacity={cloudOpacity}
        speed={scene === 'storm' ? 2.4 : 1}
      />
      {palette.rain > 0 && scene !== 'snow' && (
        <Rain count={palette.rain} slant={scene === 'storm' ? 0.5 : 0.2} speed={scene === 'storm' ? 20 : 13} />
      )}
      {scene === 'snow' && <Rain count={palette.rain} colour="#e2e8f0" slant={0.06} speed={2.4} />}
      {scene === 'storm' && <Lightning />}
      {scene === 'heat' && <HeatHaze />}
    </>
  )
}

export default function WeatherScene({ scene = 'clear', intensity = 1, light = false, className = '' }) {
  const reduced = useReducedMotion()
  const [webglFailed, setWebglFailed] = useState(false)
  const palette = paletteFor(scene)

  // On a light theme the scene's own dark palette would fight the interface,
  // so the ground comes from the theme variables and only the weather motion
  // (clouds, rain) stays scene-specific.
  const gradient = light
    ? {
        background:
          'radial-gradient(120% 90% at 50% -10%, var(--wx-bg-deep) 0%, var(--wx-bg) 58%, var(--wx-bg) 100%)',
      }
    : {
        background: `radial-gradient(120% 90% at 50% -10%, ${palette.top} 0%, ${palette.bottom} 62%, var(--wx-bg-deep) 100%)`,
      }

  return (
    <div className={`pointer-events-none fixed inset-0 -z-10 ${className}`} aria-hidden="true">
      {/* Always painted: the canvas is an enhancement on top of this. */}
      <div className="absolute inset-0 transition-[background] duration-1000" style={gradient} />

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
            <SceneContents scene={scene} light={light} />
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
