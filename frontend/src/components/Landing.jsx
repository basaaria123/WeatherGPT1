import { motion } from 'framer-motion'
import { t } from '../i18n/ui'
import { useStore } from '../store/useStore'

/**
 * Landing page.
 *
 * The brief is that a judge understands what / why / who within ten seconds, so
 * the hierarchy is deliberate: one sentence of what it is, one line of who it
 * serves, then the three-stage thesis as three scannable cards. Everything else
 * is below the fold.
 */

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  show: (delay = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] },
  }),
}

export default function Landing({ onEnter, onDemo }) {
  const language = useStore((s) => s.language)

  const pillars = [
    { key: 'data', title: t(language, 'pillarDataTitle'), body: t(language, 'pillarDataBody'), icon: '◵' },
    { key: 'understand', title: t(language, 'pillarUnderstandTitle'), body: t(language, 'pillarUnderstandBody'), icon: '◈' },
    { key: 'action', title: t(language, 'pillarActionTitle'), body: t(language, 'pillarActionBody'), icon: '➜' },
  ]

  return (
    <main className="relative mx-auto flex min-h-dvh w-full max-w-6xl flex-col px-5 pb-14 pt-8 sm:px-8">
      <motion.header
        variants={fadeUp}
        initial="hidden"
        animate="show"
        className="flex items-center justify-between gap-4"
      >
        <div className="flex items-center gap-2.5">
          <span className="text-lg font-semibold tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>
            Weather<span className="text-primary">GPT</span>
          </span>
        </div>
      </motion.header>

      <div className="flex flex-1 flex-col justify-center py-12 sm:py-16">
        <motion.p
          variants={fadeUp}
          initial="hidden"
          animate="show"
          custom={0.1}
          className="mb-4 text-[11px] font-semibold uppercase tracking-[0.24em] text-primary"
        >
          {t(language, 'tagline')}
        </motion.p>

        <motion.h1
          variants={fadeUp}
          initial="hidden"
          animate="show"
          custom={0.18}
          className="max-w-[16ch] text-balance text-[2.6rem] leading-[1.05] sm:text-6xl lg:text-7xl"
        >
          {t(language, 'heroTitle')}
        </motion.h1>

        <motion.p
          variants={fadeUp}
          initial="hidden"
          animate="show"
          custom={0.26}
          className="mt-6 max-w-2xl text-balance text-base leading-relaxed text-ink-soft sm:text-lg"
        >
          {t(language, 'heroLead')}
        </motion.p>

        <motion.p
          variants={fadeUp}
          initial="hidden"
          animate="show"
          custom={0.32}
          className="mt-3 max-w-2xl text-sm text-muted"
        >
          {t(language, 'heroWho')}
        </motion.p>

        <motion.div
          variants={fadeUp}
          initial="hidden"
          animate="show"
          custom={0.4}
          className="mt-9 flex flex-wrap items-center gap-3"
        >
          <button
            type="button"
            onClick={onEnter}
            className="rounded-[var(--radius-pill)] bg-primary px-6 py-3 text-sm font-semibold text-[#04121d]
                       shadow-[0_8px_28px_rgb(34_211_238/0.32)] transition hover:brightness-110
                       focus-visible:outline-offset-4 active:scale-[0.98]"
          >
            {t(language, 'heroCta')} →
          </button>
          <button
            type="button"
            onClick={onDemo}
            className="rounded-[var(--radius-pill)] border border-white/15 bg-white/[0.05] px-6 py-3
                       text-sm font-medium text-ink transition hover:border-white/30 hover:bg-white/[0.1]"
          >
            {t(language, 'heroSecondary')}
          </button>
        </motion.div>

      </div>

      <motion.div
        variants={fadeUp}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true }}
        custom={0.1}
        className="grid gap-3 sm:grid-cols-3"
      >
        {pillars.map((pillar, index) => (
          <motion.article
            key={pillar.key}
            variants={fadeUp}
            custom={0.1 + index * 0.08}
            className="glass p-5"
          >
            <div className="mb-3 flex items-center gap-2.5">
              <span
                aria-hidden="true"
                className="grid h-8 w-8 place-items-center rounded-lg bg-primary/12 text-sm text-primary"
              >
                {pillar.icon}
              </span>
              <h2 className="text-sm font-semibold text-ink">{pillar.title}</h2>
            </div>
            <p className="text-xs leading-relaxed text-muted">{pillar.body}</p>
          </motion.article>
        ))}
      </motion.div>

      <p className="mt-8 text-center text-[11px] leading-relaxed text-faint">
        {t(language, 'disclaimer')}
      </p>
    </main>
  )
}
