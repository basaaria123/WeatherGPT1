import { motion } from 'framer-motion'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { LAYERS, LAYER_ORDER } from './map/mapLayers'

/**
 * The dashboard's doorway to the map page.
 *
 * The map used to sit inline, a 20rem panel between the reading and the role
 * advice — big enough to push everything below it off the first screen, small
 * enough that panning it was awkward. It now has a page of its own, and this
 * is what is left in its place: a single control that says what is behind it.
 *
 * It renders nothing while the map has no data, for the same reason the map
 * itself did: a door onto an empty room is worse than no door.
 */
export default function MapLauncher({ ready, onOpen }) {
  const language = useStore((s) => s.language)
  if (!ready) return null

  return (
    <motion.button
      type="button"
      onClick={onOpen}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
      className="group flex w-full min-w-0 items-center gap-4 rounded-[var(--radius-card)] border
                 border-[rgb(var(--wx-tint)/0.08)] bg-[rgb(var(--wx-tint)/0.035)] px-4 py-3.5 text-left
                 transition hover:border-primary/40 hover:bg-primary/[0.06]"
    >
      <span
        aria-hidden="true"
        className="grid h-11 w-11 shrink-0 place-items-center rounded-[var(--radius-card)]
                   border border-[rgb(var(--wx-tint)/0.10)] bg-[rgb(var(--wx-tint)/0.05)] text-lg"
      >
        🗺️
      </span>

      <span className="min-w-0 flex-1">
        <span className="block truncate text-[14px] font-semibold text-ink">
          {t(language, 'weatherMap')}
        </span>
        <span className="mt-0.5 block text-[12px] leading-snug text-muted">
          {t(language, 'mapLead')}
        </span>
        {/* The layers named rather than described: it is the quickest way to
            say what the page holds without opening it. */}
        <span className="mt-1.5 flex flex-wrap gap-1">
          {LAYER_ORDER.map((id) => (
            <span
              key={id}
              className="rounded-[var(--radius-pill)] border border-[rgb(var(--wx-tint)/0.10)]
                         bg-[rgb(var(--wx-tint)/0.04)] px-1.5 py-px text-[10px] text-faint"
            >
              {LAYERS[id].icon} {t(language, LAYERS[id].labelKey)}
            </span>
          ))}
        </span>
      </span>

      <span
        aria-hidden="true"
        className="shrink-0 text-[15px] text-muted transition group-hover:translate-x-0.5 group-hover:text-primary"
      >
        →
      </span>
    </motion.button>
  )
}
