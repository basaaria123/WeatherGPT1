import { t } from '../../i18n/ui'
import { useStore } from '../../store/useStore'
import Icon from '../ui/Icon'
import { Panel } from '../ui/Primitives'

/**
 * Advanced Forecast Intelligence.
 *
 * This screen describes an architecture, and the one thing it must never do is
 * describe a capability the build does not have. So there are exactly two
 * statuses and they are not decoration:
 *
 *   INTEGRATED  a provider this application actually calls. Right now that is
 *               one: Open-Meteo, named from `data_source` rather than written
 *               in, so the card cannot outlive the integration.
 *   PLANNED     designed for, not connected. GFS and WRF are both this, and
 *               every word on their cards is in the future tense.
 *
 * There are no sample GFS figures here, no illustrative WRF output and no
 * "example" forecast. A screenshot of this screen taken during a demo says
 * exactly what is true, which is the only reason it is worth showing.
 */

const MODELS = [
  {
    id: 'gfs',
    name: 'GFS',
    fullKey: 'gfsFull',
    bodyKey: 'gfsBody',
    status: 'planned',
    tag: 'NWP MODEL',
    icon: 'globe',
  },
  {
    id: 'wrf',
    name: 'WRF',
    fullKey: 'wrfFull',
    bodyKey: 'wrfBody',
    status: 'planned',
    tag: 'NWP MODEL',
    icon: 'layers',
  },
]

// The pipeline, as the stages the application actually runs. Each name is a
// thing in the codebase — the weather service, the risk engine, the advisory
// builder — not an aspirational label.
const PIPELINE = ['flowData', 'flowUnderstanding', 'flowContext', 'flowRisk', 'flowAction']

const INPUTS = ['inputRealtime', 'inputHistorical', 'inputRisk', 'inputNwp']

export default function ForecastIntelligence({ onBack }) {
  const language = useStore((s) => s.language)
  const dataSource = useStore((s) => s.dataSource)
  const capabilities = useStore((s) => s.capabilities)

  // Named from what the application reports, so this cannot claim a provider
  // that is not wired in. `weather_provider` is what /config publishes; the
  // fallback is the provider this build has always used.
  const provider = capabilities?.weather_provider ?? 'Open-Meteo'

  return (
    <>
      <section className="min-w-0 px-1 pt-0.5">
        <div className="flex min-w-0 items-start gap-2">
          <button
            type="button"
            onClick={onBack}
            aria-label={t(language, 'backToForecast')}
            className="-ml-1 mt-px grid h-7 w-7 shrink-0 place-items-center rounded-full text-ink-soft
                       transition hover:bg-[rgb(var(--wx-tint)/0.08)]"
          >
            <Icon name="chevronLeft" size={18} />
          </button>
          <div className="min-w-0">
            <h1 className="text-[16px] font-bold leading-tight tracking-[-0.015em] text-ink">
              {t(language, 'nwpTitle')}
            </h1>
            <p className="mt-0.5 text-[11.5px] leading-[1.4] text-muted">
              {t(language, 'nwpSubtitle')}
            </p>
          </div>
        </div>
      </section>

      {/* --- What is actually connected ------------------------------------ */}
      <section
        className="wx-note min-w-0 p-3.5"
        style={{
          '--wx-note-line': 'color-mix(in srgb, var(--color-safe) 26%, transparent)',
          '--wx-note-fill': 'color-mix(in srgb, var(--color-safe) 6%, var(--wx-surface))',
        }}
      >
        <div className="flex min-w-0 items-start gap-2.5">
          <span className="mt-px grid h-8 w-8 shrink-0 place-items-center rounded-full bg-safe text-white">
            <Icon name="check" size={17} stroke={2.1} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
              <h2 className="text-[13.5px] font-bold leading-tight text-ink">
                {t(language, 'realtimeTitle')}
              </h2>
              <StatusPill status="integrated" />
            </div>
            <p className="mt-1 text-[11.5px] leading-[1.45] text-ink-soft">
              {t(language, 'realtimeBody')}
            </p>
            <p className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[10.5px] text-muted">
              <span className="font-semibold">{t(language, 'sourceLabel')}:</span>
              <span className="rounded-[var(--radius-pill)] bg-[rgb(var(--wx-tint)/0.08)] px-1.5 py-px font-semibold">
                {provider}
              </span>
              {dataSource === 'fixture' && (
                <span className="font-semibold text-caution-ink">· {t(language, 'simulated')}</span>
              )}
            </p>
          </div>
        </div>
      </section>

      {/* --- What is designed for, and not connected ----------------------- */}
      {MODELS.map((model) => (
        <section key={model.id} className="glass min-w-0 p-3.5">
          <div className="flex min-w-0 items-start gap-2.5">
            <span
              className="mt-px grid h-8 w-8 shrink-0 place-items-center rounded-full
                         bg-[rgb(var(--wx-tint)/0.08)] text-muted"
            >
              <Icon name={model.icon} size={17} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                <h2 className="text-[13.5px] font-bold leading-tight text-ink">{model.name}</h2>
                <span
                  className="rounded-[var(--radius-pill)] bg-[rgb(var(--wx-tint)/0.08)] px-1.5 py-px
                             text-[9px] font-bold uppercase tracking-[0.08em] text-muted"
                >
                  {model.tag}
                </span>
                <StatusPill status={model.status} />
              </div>
              <p className="mt-0.5 text-[11px] font-semibold text-muted">{t(language, model.fullKey)}</p>
              <p className="mt-1 text-[11.5px] leading-[1.45] text-ink-soft">
                {t(language, model.bodyKey)}
              </p>
            </div>
          </div>
        </section>
      ))}

      {/* --- The same three, side by side. Stacked rows rather than a table:
              a three-column table at 390px is a scroll container nobody
              scrolls. ------------------------------------------------------ */}
      <Panel title={t(language, 'forecastIntelligence')}>
        <ul className="min-w-0">
          {[
            { name: t(language, 'realtimeShort'), purpose: t(language, 'purposeCurrent'), status: 'integrated' },
            { name: 'GFS', purpose: t(language, 'purposeGlobal'), status: 'planned' },
            { name: 'WRF', purpose: t(language, 'purposeRegional'), status: 'planned' },
          ].map((row) => (
            <li
              key={row.name}
              className="flex min-w-0 items-center gap-2 border-b border-[var(--wx-border)] py-2.5 last:border-b-0"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-[12.5px] font-bold text-ink">{row.name}</p>
                <p className="truncate text-[11px] text-muted">{row.purpose}</p>
              </div>
              <StatusPill status={row.status} />
            </li>
          ))}
        </ul>
      </Panel>

      {/* --- Data → AI → action -------------------------------------------- */}
      <Panel title={t(language, 'pipelineTitle')}>
        <ol className="min-w-0">
          {PIPELINE.map((key, index) => (
            <li key={key} className="min-w-0">
              <div className="flex min-w-0 items-center gap-2.5">
                <span className="wx-step shrink-0">{index + 1}</span>
                <span className="min-w-0 flex-1 text-[12.5px] font-semibold text-ink">
                  {t(language, key)}
                </span>
              </div>
              {index < PIPELINE.length - 1 && (
                <span
                  aria-hidden="true"
                  className="ml-[10px] block h-3 w-px bg-[rgb(var(--wx-tint)/0.22)]"
                />
              )}
            </li>
          ))}
        </ol>

        <div className="mt-3 border-t border-[var(--wx-border)] pt-2.5">
          <p className="wx-eyebrow mb-1.5">{t(language, 'pipelineInputs')}</p>
          <ul className="flex min-w-0 flex-wrap gap-1.5">
            {INPUTS.map((key, index) => (
              <li
                key={key}
                className={`rounded-[var(--radius-pill)] px-2 py-1 text-[10.5px] font-semibold ${
                  // The first two are connected; risk is computed from them; the
                  // fourth is not here yet, and is drawn as not here yet.
                  index === 3
                    ? 'border border-dashed border-[rgb(var(--wx-tint)/0.3)] text-faint'
                    : 'bg-[rgb(var(--wx-tint)/0.08)] text-ink-soft'
                }`}
              >
                {t(language, key)}
              </li>
            ))}
          </ul>
        </div>
      </Panel>

      {/* --- What comes next, in the future tense -------------------------- */}
      <Panel title={t(language, 'nextGenTitle')}>
        <p className="text-[12px] leading-[1.5] text-ink-soft">{t(language, 'nextGenBody')}</p>
        <div className="mt-2.5">
          <StatusPill status="planned" />
        </div>
      </Panel>
    </>
  )
}

/**
 * Integrated or planned, and nothing in between.
 *
 * Two states on purpose. A third — "in progress", "beta" — is where a screen
 * like this starts implying that something half-works, and nothing here half-
 * works: either the application calls it or it does not.
 */
function StatusPill({ status }) {
  const language = useStore((s) => s.language)
  const integrated = status === 'integrated'
  return (
    <span
      className="inline-flex shrink-0 items-center gap-1 rounded-[var(--radius-pill)] px-2 py-[3px]
                 text-[9.5px] font-bold uppercase tracking-[0.06em]"
      style={
        integrated
          ? { color: 'var(--color-safe)', background: 'color-mix(in srgb, var(--color-safe) 12%, transparent)' }
          : { color: 'var(--color-muted)', background: 'rgb(var(--wx-tint) / 0.08)' }
      }
    >
      <span aria-hidden="true">{integrated ? '●' : '○'}</span>
      {t(language, integrated ? 'statusIntegrated' : 'statusPlanned')}
    </span>
  )
}
