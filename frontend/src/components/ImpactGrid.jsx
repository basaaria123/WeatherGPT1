import { AnimatePresence, motion } from 'framer-motion'
import { useState } from 'react'
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

export default function ImpactGrid({ impacts, loading }) {
  const language = useStore((s) => s.language)
  const userType = useStore((s) => s.userType)
  // Guidance was being clipped to three lines with the rest only reachable as a
  // title tooltip — useless on touch. One card opens at a time.
  const [openCategory, setOpenCategory] = useState(null)

  return (
    <Panel title={t(language, 'weatherImpact')}>
      {!impacts?.length ? (
        <EmptyState
          icon="◵"
          message={loading ? t(language, 'insightLoading') : t(language, 'loading')}
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
            {impacts.map((impact, index) => {
              const tone = statusOf(impact.status)
              const leads = index === 0 && userType && userType !== 'general'
              const isOpen = openCategory === impact.category
              return (
                <motion.article
                  key={impact.category}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, delay: index * 0.06 }}
                  className={`rounded-xl border ${isOpen ? 'sm:col-span-2 lg:col-span-2' : ''}`}
                  style={{
                    borderColor: isOpen ? tone.color : 'rgb(var(--wx-tint) / 0.07)',
                    background: tone.tint,
                  }}
                >
                  <button
                    type="button"
                    onClick={() => setOpenCategory(isOpen ? null : impact.category)}
                    aria-expanded={isOpen}
                    className="w-full cursor-pointer p-3 text-left"
                  >
                    <div className="mb-1.5 flex items-center gap-1.5">
                      <span aria-hidden="true" className="text-sm">{ICONS[impact.category] ?? '◆'}</span>
                      <h3 className="min-w-0 truncate text-[12px] font-semibold text-ink">{impact.category}</h3>
                      {leads && (
                        <span className="ml-auto shrink-0 rounded-[var(--radius-pill)] border border-primary/40
                                         bg-primary/10 px-1.5 py-px text-[10px] font-semibold text-primary">
                          {t(language, 'forYou')}
                        </span>
                      )}
                    </div>
                    <StatusPill status={impact.status} label={impact.headline} />

                    <AnimatePresence initial={false} mode="wait">
                      <motion.p
                        key={isOpen ? 'full' : 'clamped'}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.18 }}
                        className={`mt-1.5 text-[11px] leading-relaxed text-muted ${
                          isOpen ? '' : 'line-clamp-3'
                        }`}
                      >
                        {impact.detail}
                      </motion.p>
                    </AnimatePresence>

                    <span className="mt-1.5 inline-block text-[10px] font-medium text-primary">
                      {isOpen ? t(language, 'showLess') : t(language, 'showMore')} {isOpen ? '▴' : '▾'}
                    </span>
                  </button>
                </motion.article>
              )
            })}
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-faint">{t(language, 'disclaimer')}</p>
        </>
      )}
    </Panel>
  )
}
