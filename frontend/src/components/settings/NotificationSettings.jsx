import { maskPhone } from '../../auth/session'
import { t } from '../../i18n/ui'
import { useStore } from '../../store/useStore'
import { Panel } from '../ui/Primitives'

/**
 * How a warning reaches you when the app is closed.
 *
 * One component, two homes: the profile menu in the header and the Settings
 * tab of the alerts destination. Two copies would be two places to change a
 * switch and one place to forget, and a reader who turned SMS on in the header
 * would find it off in Settings.
 */
export default function NotificationSettings({ onSignIn }) {
  const language = useStore((s) => s.language)
  const session = useStore((s) => s.session)
  const signedIn = Boolean(session?.phone)

  const smsOptIn = useStore((s) => s.smsOptIn)
  const setSmsOptIn = useStore((s) => s.setSmsOptIn)
  const spokenAdvice = useStore((s) => s.spokenAdvice)
  const setSpokenAdvice = useStore((s) => s.setSpokenAdvice)
  const audibleAlerts = useStore((s) => s.audibleAlerts)
  const setAudibleAlerts = useStore((s) => s.setAudibleAlerts)
  const voiceQuestions = useStore((s) => s.voiceQuestions)
  const setVoiceQuestions = useStore((s) => s.setVoiceQuestions)
  const locationName = useStore((s) => s.location?.name)

  return (
    <Panel title={t(language, 'tabSettings')}>
      {/* --- Who this is for ------------------------------------------- */}
      <div className="flex items-center justify-between gap-3 border-b border-[var(--wx-border)] pb-3">
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-[0.14em] text-faint">
            {t(language, 'myWeatherGPT')}
          </p>
          <p className="mt-0.5 truncate text-[13.5px] font-semibold text-ink">
            {signedIn ? maskPhone(session.phone) : t(language, 'guest')}
          </p>
        </div>
        {!signedIn && onSignIn && (
          <button
            type="button"
            onClick={onSignIn}
            className="shrink-0 text-[12px] font-medium text-primary transition hover:opacity-80"
          >
            {t(language, 'signIn')} →
          </button>
        )}
      </div>

      {/* --- Where alerts are watched ----------------------------------- */}
      <Section label={t(language, 'watchedLocation')}>
        <p className="text-[12.5px] text-ink">{locationName}</p>
        <p className="mt-0.5 text-[11px] leading-relaxed text-muted">
          {t(language, 'locationSubscriptionNote')}
        </p>
      </Section>

      {/* --- SMS: the channel that works with the app closed ------------ */}
      <Section label={t(language, 'smsAlerts')}>
        <div className="flex items-center justify-between gap-3">
          <span className="text-[12.5px] font-medium text-ink">{t(language, 'smsAlerts')}</span>
          {signedIn ? (
            <Switch checked={smsOptIn} onChange={setSmsOptIn} label={t(language, 'smsAlerts')} />
          ) : (
            <span className="shrink-0 text-[11px] text-faint">{t(language, 'smsOff')}</span>
          )}
        </div>
        {signedIn ? (
          <>
            <p className="mt-1 text-[11px] text-muted">
              {smsOptIn ? t(language, 'smsHighOnly') : t(language, 'smsOff')}
            </p>
            {/* Never claim a message was sent when nothing can send one. */}
            <p className="mt-1.5 text-[10.5px] leading-relaxed" style={{ color: 'var(--color-caution-ink)' }}>
              {t(language, 'smsMockNote')}
            </p>
          </>
        ) : (
          <p className="mt-1 text-[11px] leading-relaxed text-muted">
            {t(language, 'smsGuestBlocked')}
          </p>
        )}
      </Section>

      {/* --- Voice ------------------------------------------------------ */}
      <Section label={t(language, 'voiceAndAudio')}>
        <AudioRow icon="🔊" label={t(language, 'prefSpokenAdvice')} checked={spokenAdvice} onChange={setSpokenAdvice} />
        <AudioRow icon="🚨" label={t(language, 'prefAudibleAlerts')} checked={audibleAlerts} onChange={setAudibleAlerts} />
        <AudioRow icon="🎙" label={t(language, 'prefVoiceQuestions')} checked={voiceQuestions} onChange={setVoiceQuestions} />
        <p className="mt-1.5 text-[10.5px] leading-relaxed text-faint">
          {t(language, 'audioNeverAutoplays')}
        </p>
      </Section>
    </Panel>
  )
}

function Section({ label, children }) {
  return (
    <div className="border-b border-[var(--wx-border)] py-3 last:border-b-0 last:pb-0">
      <p className="mb-1.5 text-[10px] uppercase tracking-[0.14em] text-faint">{label}</p>
      {children}
    </div>
  )
}

export function Switch({ checked, onChange, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative h-[22px] w-10 shrink-0 rounded-full border transition ${
        checked
          ? 'border-primary/60 bg-primary/20'
          : 'border-[var(--wx-border)] bg-[rgb(var(--wx-tint)/0.06)]'
      }`}
    >
      <span
        aria-hidden="true"
        className="absolute top-[2px] h-[16px] w-[16px] rounded-full transition-all"
        style={{
          left: checked ? '20px' : '2px',
          background: checked ? 'var(--color-primary)' : 'rgb(var(--wx-tint) / 0.35)',
        }}
      />
    </button>
  )
}

export function AudioRow({ icon, label, checked, onChange }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <span className="flex min-w-0 items-center gap-2 text-[12.5px] text-ink">
        <span aria-hidden="true" className="shrink-0">{icon}</span>
        <span className="truncate">{label}</span>
      </span>
      <Switch checked={checked} onChange={onChange} label={label} />
    </div>
  )
}
