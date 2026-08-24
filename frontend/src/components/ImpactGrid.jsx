import { motion } from 'framer-motion'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'
import { statusOf } from './ui/severity'
import { EmptyState, Panel, StatusPill } from './ui/Primitives'

/**
 * Sector impact cards.
 *
 * Rendered purely from what the backend returns, so adding a category server
 * side needs no change here — and a category the backend cannot support simply
 * does not appear, rather than being invented in the UI.
 */

const ICONS = {
  Farming: '🌾', Fishing: '🎣', Travel: '🚗', Household: '🏠', 'Outdoor activity': '🚶',
  खेती: '🌾', 'मछली पकड़ना': '🎣', यात्रा: '🚗', 'घर-गृहस्थी': '🏠', 'बाहरी गतिविधि': '🚶',
  వ్యవసాయం: '🌾', 'చేపల వేట': '🎣', ప్రయాణం: '🚗', 'ఇంటి పనులు': '🏠', 'బయటి కార్యకలాపాలు': '🚶',
  কৃষিকাজ: '🌾', 'মাছ ধরা': '🎣', যাত্রা: '🚗', 'ঘরের কাজ': '🏠', 'বাইরের কাজকর্ম': '🚶',
  शेती: '🌾', मासेमारी: '🎣', प्रवास: '🚗', घरकाम: '🏠', 'बाहेरील हालचाल': '🚶',
  কৃষি: '🌾', 'মাছ ধৰা': '🎣', যাত্ৰা: '🚗', 'ঘৰুৱা কাম': '🏠', 'বাহিৰৰ কাম': '🚶',
}

export default function ImpactGrid({ impacts }) {
  const language = useStore((s) => s.language)

  return (
    <Panel title={t(language, 'weatherImpact')}>
      {!impacts?.length ? (
        <EmptyState icon="◵" message="Impact guidance appears once conditions have loaded." />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
            {impacts.map((impact, index) => {
              const tone = statusOf(impact.status)
              return (
                <motion.article
                  key={impact.category}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, delay: index * 0.06 }}
                  title={impact.detail}
                  className="rounded-xl border p-3"
                  style={{ borderColor: 'rgb(255 255 255 / 0.07)', background: tone.tint }}
                >
                  <div className="mb-1.5 flex items-center gap-1.5">
                    <span aria-hidden="true" className="text-sm">{ICONS[impact.category] ?? '◆'}</span>
                    <h3 className="min-w-0 truncate text-[11px] font-semibold text-ink">{impact.category}</h3>
                  </div>
                  <StatusPill status={impact.status} label={impact.headline} />
                  <p className="mt-1.5 line-clamp-3 text-[10px] leading-relaxed text-muted">{impact.detail}</p>
                </motion.article>
              )
            })}
          </div>
          <p className="mt-3 text-[10px] leading-relaxed text-faint">{t(language, 'disclaimer')}</p>
        </>
      )}
    </Panel>
  )
}
